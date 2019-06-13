import fnmatch
import logging
import os
import time
from typing import List
from uuid import uuid4

from kit.backends.kusto import KustoBackend
from kit.enums import DataConflictMode, SchemaConflictMode
from kit.exceptions import DatabaseDoesNotExist, DatabaseConflictError, TableConflictError
from kit.helpers import human_readable
from kit.models.data_source import DataSource, DataEntity
from kit.models.ingestion import IngestionManifest

logger = logging.getLogger("kit")


class FolderIngestionFlow:
    def __init__(self, folder: str, target_cluster: str, target_db: str = None, auth: dict = None, **kwargs):
        self.folder = os.path.normpath(folder)
        self.target_db = target_db or os.path.basename(folder)
        self.target_cluster = target_cluster
        self.auth = auth
        self.kusto_backend = KustoBackend(target_cluster, auth)
        self.data_conflict = kwargs.get("data_conflict_mode", DataConflictMode.Safe)
        self.schema_conflict = kwargs.get("data_conflict_mode", SchemaConflictMode.Append)
        self.no_wait = kwargs.get("no_wait", False)
        self.direct = kwargs.get("direct", False)
        self.pattern = kwargs.get("pattern", None)
        self.headers = kwargs.get("headers", False)

    def ensure_folder(self):
        files = os.listdir(self.folder)

        if self.pattern:
            files = [f for f in os.listdir(self.folder) if fnmatch.fnmatch(f, self.pattern)]

        total = 0

        logger.info(f'Folder "{self.folder}" contains {len(files)} files : ')
        for index, file in enumerate(sorted(files)):
            file_path = os.path.join(self.folder, file)
            file_size = os.stat(file_path).st_size
            total += file_size
            logger.info(f"  [{index + 1}/{len(files)}] {file} {human_readable(file_size)}")

        logger.info(f'Folder "{self.folder}" total size {human_readable(total)}')

    def run(self):
        self.ensure_folder()

        data_source = DataSource.from_path(self.folder, conflict_mode=self.data_conflict, pattern=self.pattern, headers=self.headers)
        target_schema = self.kusto_backend.describe_database(self.target_db)

        # TODO: this is somewhat misleading (probably the hardest part here).
        #  we try and match sources with target_database and creating auto-mappings
        manifest = IngestionManifest.from_source_and_database(data_source, target_schema)

        manifest_flow = ManifestIngestionFlow(
            manifest,
            target_cluster=self.target_cluster,
            auth=self.auth,
            schema_conflict=self.schema_conflict,
            direct=self.direct,
            no_wait=self.no_wait,
        )

        manifest_flow.run()


class FilesIngestionFlow:
    def __init__(self, files: List[str], target_cluster: str, target_db: str, target_table: str = None, auth: dict = None, **kwargs):
        self.files = files
        self.target_db = target_db
        self.target_cluster = target_cluster
        self.target_table = target_table
        self.auth = auth
        self.kusto_backend = KustoBackend(target_cluster, auth)
        self.data_conflict = kwargs.get("data_conflict_mode", DataConflictMode.Safe)
        self.schema_conflict = kwargs.get("data_conflict_mode", SchemaConflictMode.Append)
        self.no_wait = kwargs.get("no_wait", False)
        self.direct = kwargs.get("direct", False)
        self.headers = kwargs.get("headers", False)

    def ensure_folder(self):
        total = 0

        if len(self.files) == 0:
            raise ValueError("No files found")

        logger.info(f'Got {len(self.files)} files : ')
        for index, file in enumerate(sorted(self.files)):
            file_size = os.stat(file).st_size
            total += file_size
            logger.info(f"  [{index + 1}/{len(self.files)}] {file} {human_readable(file_size)}")

        if total == 0:
            raise ValueError("All files are empty")

        logger.info(f'Total size {human_readable(total)}')

    def run(self):
        self.ensure_folder()

        entities = []

        for f in self.files:
            entities.append(DataEntity.from_path(f, conflict_mode=self.data_conflict, headers=self.headers))

        # If explicitly specified, it means all files are part of the same entity,
        # otherwise, each file is it's own entity.
        if self.target_table:
            entity = entities.pop()
            while len(entities) > 0:
                next_entity = entities.pop()
                entity.merge(next_entity)

            entities = [entity]

        target_schema = self.kusto_backend.describe_database(self.target_db)

        # TODO: this is somewhat misleading (probably the hardest part here).
        #  we try and match sources with target_database and creating auto-mappings
        manifest = IngestionManifest.from_entities_and_database(entities, target_schema)

        manifest_flow = ManifestIngestionFlow(
            manifest,
            target_cluster=self.target_cluster,
            auth=self.auth,
            schema_conflict=self.schema_conflict,
            direct=self.direct,
            no_wait=self.no_wait,
        )

        manifest_flow.run()


class ManifestIngestionFlow:
    # TODO: passing around kusto connection is annoying. should be a singleton somewhere
    def __init__(
        self, manifest: IngestionManifest, target_cluster: str, auth: dict = None, **kwargs
    ):
        self.manifest = manifest
        self.auth = auth
        self.kusto_backend = KustoBackend(target_cluster, auth)
        self.target_cluster = target_cluster
        self.schema_conflict = kwargs.get("schema_conflict", SchemaConflictMode.Append)
        self.direct = kwargs.get("direct", False)
        self.no_wait = kwargs.get("no_wait", False)

    # TODO: perhapses logic should be abstracted away to a database object
    def prepare_database(self):
        for manifest_database in self.manifest.databases:
            try:
                target_database = self.kusto_backend.describe_database(manifest_database.name)

                for manifest_table in manifest_database.tables:
                    if manifest_table.name not in target_database.tables_dict:
                        self.kusto_backend.create_table(manifest_table, target_database.name)
                    else:
                        target_table = target_database.tables_dict[manifest_table.name]

                        if (
                            len(manifest_table.columns) > len(target_table.columns)
                            and self.schema_conflict == SchemaConflictMode.Safe
                        ):
                            raise TableConflictError(
                                f'SAFE_MODE: Manifest for "{manifest_table.name}" has more columns than actual table in {target_database}.'
                            )
                try:
                    manifest_database.assert_eq(other=target_database, allow_partial=True)
                except DatabaseConflictError:
                    if self.schema_conflict == SchemaConflictMode.Safe:
                        raise DatabaseConflictError(f"Target database has a different backends then expected")
            except DatabaseDoesNotExist:
                if self.schema_conflict == SchemaConflictMode.Safe:
                    raise DatabaseConflictError(
                        f'SAFE_MODE: Expected a Database named "{manifest_database.name}" on {self.target_cluster} but none found'
                    )
                if self.schema_conflict == SchemaConflictMode.Append:
                    # by default, if we can't find a database on the cluster, we will create it
                    raise NotImplementedError()

    def ingest_operations(self) -> str:
        batch_id = str(int(time.time())) + "_" + str(uuid4())
        logger.info(f"Batch id for monitoring : {batch_id}")
        for operation in self.manifest.operations:
            for source in operation.sources:
                mapping = self.manifest.mappings_dict[source.mapping]
                self.kusto_backend.ingest_from_source(
                    source,
                    mapping,
                    target_database=operation.database,
                    target_table=operation.target,
                    direct=self.direct,
                    batch_id=batch_id,
                    no_wait=self.no_wait,
                )

        return batch_id

    def monitor_batch(self, batch_id) -> bool:
        max_retries = 3
        retry = 1
        delay = 180  # TODO: this should be estimated by data size and cluster capacity and reported to the user
        tables_pending = set(op.target for op in self.manifest.operations)

        done = len(tables_pending) == 0
        while not done and retry <= max_retries:
            time.sleep(delay)
            logger.info(f"({retry}/{max_retries}) Waiting for {len(tables_pending)} tables to finish")
            tables_done = set()
            for table in tables_pending:
                # TODO: this method is limited. when working with multiple files, this will only now when **any** file was ingested. no way to make sure **all** were ingested.
                # TODO: should probably iterate over databases as well
                # TODO: should check errors on top of successful ingestions
                count = self.kusto_backend.count_rows_with_tag(
                    database=self.manifest.databases[0].name, table=table, tag=batch_id
                )
                if count > 0:
                    logger.info(f"Table '{table}' has {count} rows ingested")
                    tables_done.add(table)

            tables_pending -= tables_done
            done = len(tables_pending) == 0
            retry += 1

        if not done:
            logger.warning(f"Some tables seem didn't finish ingestion within a reasonable time frame. {tables_pending}")

        return done

    def ensure_no_errors(self, batch_id):
        errors = self.kusto_backend.get_ingestion_errors(self.manifest.databases[0].name, tag=batch_id)

        if len(errors) > 0:
            raise RuntimeError("Errors found during ingestion", [r.to_dict() for r in errors.rows])

    def run(self):
        logger.info("Ensuring database backends is ok")
        self.kusto_backend.ping()
        logger.info("Applying schema on database")
        self.prepare_database()
        # ensure tables exist (if not, create)
        logger.info("Ingesting according to manifest")
        # TODO: should batch per database?
        batch_id = self.ingest_operations()
        if not self.no_wait:
            logger.info("Waiting for data to be ingested")
            if not self.monitor_batch(batch_id):
                logger.warning("Couldn't make sure all data is ok")

            self.ensure_no_errors(batch_id)

        # ingest files
        logger.info("Done")
