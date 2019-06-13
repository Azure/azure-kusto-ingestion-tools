from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict

from kit.enums import SchemaConflictMode
from kit.exceptions import SchemaConflictError
from kit.models.data_source import DataSource, DataEntity
from kit.models.database import Database, Table
from kit.models.mappings import IngestionMapping
from kit.models.serializable import SerializableModel

logger = logging.getLogger(__name__)


@dataclass
class IngestionSource(SerializableModel):
    files: List[str]
    mapping: str
    options: dict = field(default_factory=dict)
    data_format: str = "csv"


@dataclass
class IngestionOp(SerializableModel):
    database: str
    sources: List[IngestionSource]
    target: str


@dataclass
class IngestionManifest(SerializableModel):
    # This holds a snapshot of the database relevant for ingestion. should be matched with actual database per-ingestion.
    databases: List[Database]
    mappings: List[IngestionMapping]
    operations: List[IngestionOp]

    def __post_init__(self):
        self.load_database_lookup()
        self.load_mappings_lookup()

    @property
    def database_dict(self) -> Dict[str, Database]:
        return self._database_dict

    @property
    def mappings_dict(self) -> Dict[str, IngestionMapping]:
        return self._mappings_dict

    def load_database_lookup(self):
        self._database_dict = {}
        for database in self.databases:
            self._database_dict[database.name] = database

    def load_mappings_lookup(self):
        self._mappings_dict = {}
        for mapping in self.mappings:
            self._mappings_dict[mapping.name] = mapping

    @classmethod
    def from_entities_and_database(cls, entities: List[DataEntity], target_database: Database,
                                   conflict_mode: SchemaConflictMode = SchemaConflictMode.Append) -> IngestionManifest:
        operations = []
        mappings: Dict[str, IngestionMapping] = {}

        for entity in entities:
            sources: Dict[str, List[str]] = defaultdict(list)
            source_table = Table.from_entity(entity)

            if entity.name not in target_database.tables_dict:
                if conflict_mode == SchemaConflictMode.Safe:
                    raise SchemaConflictError(f"SAFE MODE: Table '{source_table.name}' appears in source but no in target database '{target_database.name}'")

                logger.info(f"Source has a table '{entity.name}' which target database '{target_database.name}' is missing. will create it.")

                target_table = source_table
            else:
                target_table = target_database.tables_dict[entity.name]
            # TODO: currently assuming all files under entity are of the same format and schema
            #  this assumption can change, for example if each file contains only a part of the schema,
            #  but in such a case, it will require advanced logic to match map all those partitions into a single entity
            mapping = IngestionMapping.generate_mapping(target_table, entity)
            mappings[mapping.name] = mapping

            sources[mapping.name] = [f.path for f in entity.files]

            ingestion_sources = [
                IngestionSource(s_files, s_mapping, data_format=s_mapping.split("_")[-1])
                for s_mapping, s_files in sources.items()
            ]

            operations.append(IngestionOp(target_database.name, ingestion_sources, target_table.name))

        return IngestionManifest([target_database], list(mappings.values()), operations)

    @classmethod
    def from_source_and_database(cls, source: DataSource, target_database: Database,
                                 conflict_mode: SchemaConflictMode = SchemaConflictMode.Append) -> IngestionManifest:
        operations = []
        mappings: Dict[str, IngestionMapping] = {}
        source_schema = Database.from_source(source)

        for entity in source.entities:
            sources: Dict[str, List[str]] = defaultdict(list)

            if entity.name not in target_database.tables_dict:
                if conflict_mode == SchemaConflictMode.Safe:
                    raise SchemaConflictError(f"SAFE MODE: Table '{source.name}' appears in source but no in target database '{target_database.name}'")

                logger.info(f"Source has a table '{entity.name}' which target database '{target_database.name}' is missing. will create it.")

                target_table = source_schema.tables_dict[entity.name]
                # TODO: not sure I want to add it to manifest, maybe it should be clear that ehter is a target table that doesn't exist.
                target_database.tables.append(target_table)
            else:
                target_table = target_database.tables_dict[entity.name]
            # TODO: currently assuming all files under entity are of the same format and schema
            #  this assumption can change, for example if each file contains only a part of the schema,
            #  but in such a case, it will require advanced logic to match map all those partitions into a single entity
            mapping = IngestionMapping.generate_mapping(target_table, entity)
            mappings[mapping.name] = mapping

            sources[mapping.name] = [f.path for f in entity.files]

            ingestion_sources = [
                IngestionSource(s_files, s_mapping, data_format=s_mapping.split("_")[-1])
                for s_mapping, s_files in sources.items()
            ]

            operations.append(IngestionOp(target_database.name, ingestion_sources, target_table.name))

        return IngestionManifest([target_database], list(mappings.values()), operations)
