from typing import List, Tuple

from kit.backends.kusto import KustoBackend
from kit.models.basic import Column
from kit.models.database import Table
from kit.models.ingestion import IngestionManifest


def from_manifest(manifest: IngestionManifest) -> Tuple[List[str], List[str]]:
    table_commands = {}
    mapping_commands = {}

    for op in manifest.operations:
        db = manifest.database_dict[op.database]

        expected_table = Table(op.target, [])

        for source in op.sources:
            mapping = manifest.mappings_dict[source.mapping]

            ingestion_mapping = KustoBackend.get_ingestion_mapping(source.data_format, mapping)

            mapping_commands[source.mapping] = KustoBackend.get_create_ingestion_command(
                table=op.target, mapping_name=source.mapping, column_mappings=ingestion_mapping
            )

            expected_table.extend_columns([Column.copy(col_map.target) for col_map in mapping.columns])

        if op.target not in db.tables_dict:
            table_commands[op.target] = KustoBackend.get_create_table_command(expected_table)

    return list(table_commands.values()), list(mapping_commands.values())
