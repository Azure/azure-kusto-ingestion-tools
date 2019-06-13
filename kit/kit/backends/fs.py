import os
from pathlib import Path

from kit.enums import DataConflictMode
from kit.models.data_source import DataFile
from kit.models.database import Database, Table


def table_from_path(path, name=None, conflict_mode=DataConflictMode.Safe, top=200) -> Table:
    name = name or Path(path).with_suffix("").stem
    if os.path.isdir(path):
        return table_from_folder(path, name, conflict_mode, top=top)

    return table_from_file(path, name, top=top)


def table_from_file(filepath, name=None, top=200, **kwargs) -> Table:
    path = Path(filepath)
    if not path.is_file():
        raise ValueError('Given path is not a valid file.')

    df = DataFile.from_file(filepath, **kwargs, limit=top)

    return Table(name or path.stem, df.columns)


def table_from_folder(path, name=None, conflict_mode=DataConflictMode.Safe, top=200) -> Table:
    inferred_table = Table(name, columns=[])
    for file in os.listdir(path):
        current_table = table_from_file(file, top)
        if conflict_mode == DataConflictMode.Safe:
            inferred_table.assert_eq(current_table)

    return inferred_table


def database_from_folder(path: str, conflict_mode: DataConflictMode = DataConflictMode.Safe) -> Database:
    db_name = os.path.basename(path)

    path = Path(path)

    table_paths = list(path.iterdir())

    inferred_tables = []
    for table_path in table_paths:
        inferred_tables.append(table_from_path(str(table_path), conflict_mode=conflict_mode))

    return Database(db_name, inferred_tables)
