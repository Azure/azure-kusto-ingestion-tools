import logging

import click

from kit.core.ingestion import FilesIngestionFlow, ManifestIngestionFlow
from kit.models.ingestion import IngestionManifest

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(filename)s | %(message)s", level=logging.ERROR)

logger = logging.getLogger("kit")
logger.setLevel(logging.INFO)


def auth_from_cli(app, user, host):
    from kit.helpers import get_azure_cli_auth_token

    if app:
        aad_app_id, app_key = app.split(":")
        return dict(aad_app_id=aad_app_id, app_key=app_key, authority_id="72f988bf-86f1-41af-91ab-2d7cd011db47")
    if user:
        user_id, password = user.split(":")
        return dict(user_id=user_id, password=password, authority_id="72f988bf-86f1-41af-91ab-2d7cd011db47")

    return dict(user_token=get_azure_cli_auth_token(host))


@click.group()
@click.pass_context
def main(ctx):
    pass


@main.command()
@click.option("--user", type=str)
@click.option("--app", type=str)
@click.option("--nowait", is_flag=True, default=False)
@click.option("--direct", is_flag=True, default=False)
@click.option("--host", "-h", type=str)
@click.option("--manifest", "-m", type=str)
@click.option("--files", "-f", type=str)
@click.option("--directory", "-d", type=click.Path())
@click.option("--table", "-t", type=str)
@click.option("--database", "-db", type=str)
@click.option("--pattern", type=str)
@click.option("--object-depth", "-od", type=int, default=1)
@click.option("--dry", is_flag=True, default=False)
@click.option("--headers", is_flag=True, default=False)
@click.pass_context
def ingest(ctx, headers, dry, object_depth, pattern, database, table, directory, files, manifest, host, direct, nowait, app, user):
    from kit.core.ingestion import FolderIngestionFlow

    if directory:
        flow = FolderIngestionFlow(
            directory, host, database, auth=auth_from_cli(app, user, host), direct=direct, no_wait=nowait, pattern=pattern, headers=headers, dry=dry,
            object_depth=object_depth
        )
        flow.run()
    elif files:
        flow = FilesIngestionFlow(
            files.split(','), host, database, target_table=table, auth=auth_from_cli(app, user, host), direct=direct, no_wait=nowait, headers=headers,
            object_depth=object_depth, dry=dry
        )
        flow.run()
    elif manifest:

        flow = ManifestIngestionFlow(
            manifest_path=manifest,
            target_cluster=host,
            auth=auth_from_cli(app, user, host),
            direct=direct,
            no_wait=nowait
        )

        flow.run()


@main.command()
@click.option("--manifest", "-m", type=str)
@click.pass_context
def kql(ctx, manifest):
    manifest = IngestionManifest.load(manifest)
    from kit.specifications import kql
    table_create_commands, mapping_create_commands = kql.from_manifest(manifest)

    print('// Table Creation Commands:')
    print('\n'.join(table_create_commands))
    print('')
    print('// Ingestion Mapping Creation Commands:')
    print('\n'.join(mapping_create_commands))


@main.command()
@click.option("--table", "-t", type=str)
@click.option("--database", "-db", type=str)
@click.option("--user", type=str)
@click.option("--app", type=str)
@click.option("--host", "-h", type=str)
@click.option("-n", type=str)
@click.pass_context
def top(ctx, n, host, app, user, database, table):
    auth = auth_from_cli(app, user, host)
    from kit.backends.kusto import KustoBackend

    kusto_backend = KustoBackend(host, auth)
    print(kusto_backend.peek_table(database, table, n))


@main.command()
@click.option("--table", "-t", type=str)
@click.option("--database", "-db", type=str)
@click.option("--user", type=str)
@click.option("--app", type=str)
@click.option("--host", "-h", type=str)
@click.pass_context
def count(ctx, host, app, user, database, table):
    auth = auth_from_cli(app, user, host)
    from kit.backends.kusto import KustoBackend

    kusto_backend = KustoBackend(host, auth)
    print(kusto_backend.count_rows(database, table))


@main.group()
@click.pass_context
def schema(ctx):
    pass


@schema.command()
@click.pass_context
@click.option("--user", type=str)
@click.option("--app", type=str)
@click.option("--sql", "-sql", type=str)
@click.option("--host", "-h", type=str)
@click.option("--database", "-db", type=str)
@click.option("--directory", "-d", type=click.Path())
@click.option("--file", "-f", type=click.Path())
def create(ctx, file, directory, database, host, sql, app, user):
    if file:
        # TODO: should resolve file location (can be s3 / azure storage / local file)
        from kit.backends import fs
        from kit.models.database import Database

        table = fs.table_from_file(file)

        db = Database("temp", [table])

    elif directory:
        from kit.backends import fs
        from kit.models.database import Database

        db = fs.database_from_folder(directory)
    elif host:
        auth = auth_from_cli(app, user, host)
        from kit.backends.kusto import KustoBackend

        kusto_backend = KustoBackend(host, auth)
        db = kusto_backend.describe_database(database)
    elif sql:
        import kit.specifications.sql as sql_spec

        db = sql_spec.database_from_sql(sql)
    else:
        raise ValueError("No method was chosen. use `kit schema create --help` ")

    print(db.to_json())


@schema.command()
@click.pass_context
@click.option("--user", type=str)
@click.option("--app", type=str)
@click.option("--host", "-h", type=str)
@click.option("--database", "-db", type=str)
@click.option("--file", "-f", type=click.Path())
def apply(ctx, file, database, host, app, user):
    from kit.models.database import Database
    db = Database.load(file)
    auth = auth_from_cli(app, user, host)
    from kit.backends.kusto import KustoBackend

    kusto_backend = KustoBackend(host, auth)

    # target db
    db.name = database
    kusto_backend.enforce_schema(db)


if __name__ == "__main__":
    main()
