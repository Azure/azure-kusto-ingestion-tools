from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

from kit.models.basic import Column
from kit.models.data_source import DataEntity
from kit.models.database import Table

logger = logging.getLogger(__name__)


@dataclass
class ColumnMapping:
    source: Column
    target: Column


@dataclass
class IngestionMapping:
    name: str
    columns: List[ColumnMapping]

    @classmethod
    def generate_mapping(cls, table: Table, source: DataEntity) -> IngestionMapping:
        data_format = source.files[0].data_format
        name = source.name + "_from_" + data_format

        column_mappings = []
        index_based = not any((c for c in source.columns if c.name is not None))

        if index_based and len(source.columns) != len(table.columns):
            logger.warning(f"Mapping for '{source.name}' used index based mapping, and column count doesn't match target table '{table.name}'. "
                           f"{len(source.columns)} != {len(table.columns)}")

        for index, source_col in enumerate(source.columns):
            if index_based:
                # TODO: should probably notify if types mismatch (might mean mis-configured)
                if index + 1 > len(table.columns):
                    raise RuntimeError(f"Target table '{table.name}' has fewer columns than source {source.name}. Failed index {index}")

                target_col = table.columns[index]
            else:
                expected_target_col_name = Table.valid_column_name(source_col.name)
                if expected_target_col_name not in table.columns_lookup:
                    raise RuntimeError(
                        f"Target table '{table.name}' is missing a column {expected_target_col_name} ({source_col.name}) from source {source.name}. Failed index {index}")

                target_col = table.columns_lookup[expected_target_col_name]
            column_mappings.append(ColumnMapping(source_col, target_col))

        return IngestionMapping(name, column_mappings)
