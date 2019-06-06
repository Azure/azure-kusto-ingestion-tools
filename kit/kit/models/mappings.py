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

        columns = []

        if data_format == 'csv':
            index_based = False
            for index, source_col in enumerate(source.columns):
                # if no name was given, wee fallback to using indices
                if source_col.name is None:
                    index_based = True
                    # TODO: should probably notify if types mistmatch (might mean mis-configured)
                    if index + 1 > len(table.columns):
                        raise RuntimeError(f"Target table '{table.name}' has fewer columns than source {source.name}. Failed index {index}")
                    columns.append(ColumnMapping(source_col, table.columns[index]))

            if index_based and len(source.columns) != len(table.columns):
                logger.warning(f"Mapping for '{source.name}'' used index based mapping, and column count doesn't match target table '{table.name}'. "
                               f"{len(source.columns)} != {len(table.columns)}")

        else:
            raise NotImplementedError('Currently only supporting csv')

        return IngestionMapping(name, columns)
