import csv
import io
from typing import List, Dict, Tuple

from pyarrow import csv as arrow_csv

from kit.dtypes import KustoType
from kit.dtypes.resolver import KustoTypeResolver
from kit.models.database import Column


class ObservedColumn:
    def __init__(self, index=None, name=None):
        self.index = index
        self.name = name
        self.observed_types = []

    def observe(self, value):
        if type(value) is str:
            self.observed_types.append(KustoTypeResolver.from_string(value))
        else:
            self.observed_types.append(KustoTypeResolver.from_python_type(value))

    def __repr__(self):
        return f"ObservedColumn(index={self.index},name='{self.name}')"


def materialize_columns(observed_columns) -> List[Column]:
    columns = []
    for observed_col in observed_columns:
        # TODO: should handle json files properly as well
        # TODO: column names should be grabbed from file if has headers
        seen_dynamic = False
        seen_number = False
        seen_decimal = False
        seen_long = False
        seen_float = False
        seen_date = False
        seen_bool = False
        seen_string = False

        data_type = KustoType.STRING

        for t in observed_col.observed_types:
            if t.is_numeric():
                seen_number = True
            elif t is KustoType.BOOL:
                seen_bool = True
            elif t is KustoType.DATETIME:
                seen_date = True
            elif t is KustoType.STRING:
                seen_string = True
            elif t is KustoType.DYNAMIC:
                seen_dynamic = True

        if not any([seen_number, seen_date, seen_string, seen_dynamic]) and seen_bool:
            data_type = KustoType.BOOL
        elif not any([seen_number, seen_bool, seen_string, seen_dynamic]) and seen_date:
            data_type = KustoType.DATETIME
        elif not any([seen_number, seen_bool, seen_string, seen_date]) and seen_dynamic:
            data_type = KustoType.DYNAMIC
        elif not any([seen_dynamic, seen_bool, seen_string, seen_date]) and seen_number:
            if seen_decimal or (seen_long and seen_float):
                data_type = KustoType.DECIMAL
            elif seen_float:
                data_type = KustoType.REAL
            elif seen_long:
                data_type = KustoType.LONG
            else:
                data_type = KustoType.INT
        else:
            data_type = KustoType.STRING

        columns.append(Column(data_type=data_type, index=observed_col.index, name=observed_col.name))

    return columns


def observe_columns_in_object(obj, observed_columns_map: Dict[str, ObservedColumn] = None, object_depth=1, path=None):
    observed_columns_map = observed_columns_map or {}

    for key, value in obj.items():
        if type(value) is dict and object_depth > 1:
            observed_columns_map = observe_columns_in_object(value, observed_columns_map, object_depth=object_depth - 1, path=key)
        else:
            name = key if path is None else path + "." + key
            if name not in observed_columns_map:
                observed_columns_map[name] = ObservedColumn(name=name)

            observed_columns_map[name].observe(value)

    return observed_columns_map


def columns_from_json_stream(stream, limit=200, object_depth=1, **kwargs) -> Tuple[List[Column], bool]:
    import ijson.backends.python as ijson
    import json

    observed_columns_map = None
    counter = 0

    first_char = stream.read(1)
    file_starts_at = 0
    while not first_char:
        file_starts_at += 1
        first_char = stream.read(1)

    stream.seek(file_starts_at, 0)
    multi_line = False
    if first_char == "[":
        # TODO: assuming data is an array ('[{...},{...},...,{}]')
        multi_line = True
        for item in ijson.items(stream, "item"):
            if limit is not None and counter >= limit:
                break

            observed_columns_map = observe_columns_in_object(item, observed_columns_map, object_depth)
            counter += 1

    else:
        line = stream.readline()
        while line and counter <= limit:
            try:
                item = json.loads(line)
                observed_columns_map = observe_columns_in_object(item, observed_columns_map, object_depth)

                counter += 1

                if counter >= limit:
                    break

                line = stream.readline()
            except:
                multi_line = True
                line += stream.readline()

    observed_columns = list(observed_columns_map.values())

    return materialize_columns(observed_columns), multi_line


def columns_from_csv_stream(stream, includes_headers=False, limit=200) -> List[Column]:
    columns = []
    first_line = None

    if isinstance(stream, io.BytesIO):
        table = arrow_csv.read_csv(stream)

        for index, field in enumerate(table.schema):
            kusto_type = KustoTypeResolver.from_arrow_type(field.type)
            columns.append(Column(name=field.name.strip(), index=index, data_type=kusto_type))
    elif isinstance(stream, (io.StringIO, io.TextIOWrapper)):
        reader = csv.reader(stream)
        observed_columns = None
        for i, line in enumerate(reader):
            # limit row scan
            if i == limit:
                break

            if i == 0 and includes_headers:
                first_line = line
                continue

            if observed_columns is None:
                observed_columns = [ObservedColumn(i, name=first_line[i] if first_line is not None else None) for i in range(len(line))]

            for col, value in enumerate(line):
                observed_columns[col].observe(value)

        columns = materialize_columns(observed_columns)

    return columns
