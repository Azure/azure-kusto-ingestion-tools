from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict

from kit.dtypes import cdm_type_to_kusto
from kit.exceptions import SchemaConflictError

from kit.models import cdm
from kit.models.basic import Column
from kit.models.data_source import DataSource, DataEntity
from kit.models.serializable import SerializableModel
import re

_column_regex = re.compile('[^0-9a-zA-Z_.-]+')

@dataclass
class Table(SerializableModel):
    name: str
    columns: List[Column]

    def __eq__(self, other: Table):
        if len(self.columns) != len(other.columns):
            return False

        for i in range(len(self.columns)):
            if self.columns[i].data_type != other.columns[i].data_type:
                return False

        return True

    def __post_init__(self):
        for col in self.columns:
            if col.name is not None:
                col.name = self.valid_column_name(col.name)

        self.columns_lookup = {col.name: col for col in self.columns}

    @classmethod
    def valid_column_name(cls, column_name):
        return _column_regex.sub('', column_name)

    def assert_eq(self, other: Table):
        if len(self.columns) != len(other.columns):
            raise SchemaConflictError(
                f"Column count mismatch for {self.name}: self is {len(self.columns)} but other is {len(other.columns)}"
            )

        for i in range(len(self.columns)):
            if self.columns[i].data_type != other.columns[i].data_type:
                raise SchemaConflictError(
                    f"Column type mismatch: [{self.columns[i].name}]  a is {self.columns[i].data_type}, b is {other.columns[i].data_type}"
                )

    @staticmethod
    def from_entity(entity: DataEntity):
        # copying array to detach reference
        return Table(entity.name, [Column.copy(c) for c in entity.columns])

    @staticmethod
    def from_cdm_entity(entity: cdm.LocalEntity, **kwargs) -> Table:
        columns = []

        for i, attr in enumerate(entity.attributes):
            columns.append(
                Column(
                    index=i, data_type=cdm_type_to_kusto(entity.attributes[i].data_type), name=entity.attributes[i].name
                )
            )

        return Table(entity.name, columns)

    def extend_columns(self, columns: List[Column]):
        for col in columns:
            if col.name not in self.columns_lookup:
                self.columns.append(col)
                self.columns_lookup[col.name] = col


@dataclass
class Database(SerializableModel):
    name: str
    tables: List[Table] = field(default_factory=list)

    def assert_eq(self, other: Database, allow_partial=True):
        if len(self.tables) != len(other.tables):
            if not allow_partial:
                raise SchemaConflictError(
                    f"Table count mismatch for {self.name}: self is {len(self.tables)} but other is {len(other.tables)}"
                )

            self_tables = set(t.name for t in self.tables)
            other_tables = set(t.name for t in self.tables)
            if not self_tables.issubset(other_tables):
                raise SchemaConflictError(f"Not all tables exist")

        for t_name, t_instance in self.tables_dict.items():
            if t_name in other.tables_dict:
                t_instance.assert_eq(other.tables_dict[t_name])

    @property
    def tables_dict(self) -> Dict[str, Table]:
        return self._tables_dict

    def __post_init__(self):
        self.load_tables()

    def load_tables(self):
        self._tables_dict = {}
        for table in self.tables:
            self._tables_dict[table.name] = table

    @staticmethod
    def from_source(source: DataSource) -> Database:
        db_name = source.name
        tables = []

        for entity in source.entities:
            tables.append(Table.from_entity(entity))

        return Database(db_name, tables)

    # @staticmethod
    # def from_cdm_model(cdm_uri, **kwargs) -> Database:
    #     tables = []
    #
    #     model_file = RemoteFile(cdm_uri)
    #     model_file.download()
    #
    #     model = cdm.Model.fromdict(model_file.data)
    #     for entity in model.entities:
    #         tables.append(Table.from_cdm_entity(entity))
    #
    #     # TODO: need to adding mappings based on scheme files
    #     return Database(model.name, tables)
