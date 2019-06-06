from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from kit.dtypes.infer import columns_from_stream
from kit.enums import DataConflictMode
from kit.exceptions import DataConflictError
from kit.models.basic import Column


@dataclass
class DataFile:
    path: str
    columns: List[Column]
    data_format: str = "csv"

    @classmethod
    def from_file(cls, path, **kwargs) -> DataFile:
        ext = os.path.splitext(path)[-1][1:]
        headers = kwargs.get('headers', False)
        with open(path, encoding='utf8') as f:
            columns = columns_from_stream(f, includes_headers=headers)

        return DataFile(path, columns, ext)


@dataclass
class DataEntity:
    name: str
    path: str
    columns: List[Column]
    files: List[DataFile]

    @classmethod
    def from_path(cls, path, conflict_mode: DataConflictMode = DataConflictMode.Safe, pattern=None, **kwargs) -> DataEntity:
        data_files = []
        columns = []
        headers = kwargs.get('headers', False)

        if os.path.isdir(path):
            name = os.path.basename(path)
            files = os.listdir(path)

            if pattern:
                files = [f for f in files if fnmatch.fnmatch(f, pattern)]

            for index, file in enumerate(files):
                file_path = os.path.join(path, file)
                df = DataFile.from_file(file_path, headers=headers)
                data_files.append(df)

                if conflict_mode == DataConflictMode.Safe:
                    # first file set the tone
                    if index == 0:
                        columns = df.columns
                    else:
                        if len(columns) != len(df.columns):
                            raise DataConflictError(
                                f"Column count mismatch for {name}: self has {len(columns)} but {df.path} has {len(df.columns)}"
                            )

                        for i in range(len(columns)):
                            if columns[i].data_type != df.columns[i].data_type:
                                raise DataConflictError(
                                    f"Column type mismatch: [{columns[i].name}] was {columns[i].data_type}, but {df.path} is {df.columns[i].data_type}"
                                )

                        columns = df.columns
                # FIXME: add merging logic

        else:
            name = Path(path).with_suffix("").stem
            df = DataFile.from_file(path, headers=headers)
            data_files = [df]
            columns = df.columns

        return DataEntity(name, path, columns, data_files)

    def merge(self, other: DataEntity):
        raise NotImplementedError()


@dataclass
class DataSource:
    name: str
    path: str
    entities: List[DataEntity]

    @classmethod
    def from_path(cls, path, conflict_mode: DataConflictMode = DataConflictMode.Safe, pattern=None, **kwargs) -> DataSource:
        name = os.path.basename(path)
        headers = kwargs.get('headers', False)
        entities = []
        if os.path.isdir(path):
            entity_paths = os.listdir(path)

            for entity_path in entity_paths:
                entity_path = Path(os.path.join(path, entity_path))
                if entity_path.is_file():
                    if entity_path.match(pattern):
                        entities.append(DataEntity.from_path(entity_path, conflict_mode=conflict_mode, headers=headers))
                else:
                    entities.append(DataEntity.from_path(entity_path, conflict_mode=conflict_mode, pattern=pattern, headers=headers))

        return DataSource(name, path, entities)
