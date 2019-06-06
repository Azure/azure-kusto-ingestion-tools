import csv
import io
import json
from typing import List

from pyarrow import csv as arrow_csv

from kit.dtypes import KustoType
from kit.dtypes.resolver import KustoTypeResolver
from kit.models.database import Column


class ObservedColumn:
    def __init__(self, index):
        self.index = index
        self.observed_types = []

    def observe(self, value):
        self.observed_types.append(KustoTypeResolver.from_string(value))


def materialize_columns(observed_columns) -> List[Column]:
    columns = []
    for observed_col in observed_columns:
        # TODO: should handle json files properly as well
        # TODO: column names should be grabbed from file if has headers
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

        if not seen_number and not seen_date and not seen_string and seen_bool:
            data_type = KustoType.BOOL
        elif not seen_number and seen_date and not seen_string and not seen_bool:
            data_type = KustoType.DATETIME
        elif seen_number and not seen_date and not seen_bool and not seen_string:
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

        columns.append(Column(data_type=data_type, index=observed_col.index))

    return columns


def observe_columns(stream, file_format="csv", limit=200, **kwargs) -> List[Column]:
    columns = []
    if file_format == "csv":
        includes_headers = kwargs.get("headers", False)
        if isinstance(stream, io.BytesIO):
            table = arrow_csv.read_csv(stream)

            for index, field in enumerate(table.schema):
                kusto_type = KustoTypeResolver.from_arrow_type(field.type)
                columns.append(Column(index, name=field.name.strip(), data_type=kusto_type.value))
        elif isinstance(stream, io.StringIO):
            reader = csv.reader(stream)
            observed_columns = None
            for i, line in enumerate(reader):
                # limit row scan
                if i == limit:
                    break

                if observed_columns is None:
                    observed_columns = [ObservedColumn(i) for i in range(len(line))]

                if i == 0 and includes_headers:
                    first_line = line
                    continue

                for col, value in enumerate(line):
                    observed_columns[col].observe(value)

            columns = materialize_columns(observed_columns)

    elif file_format == "json":
        json_object = json.load(stream)

    return columns


def columns_from_stream(stream, file_format="csv", includes_headers=False, limit=200) -> List[Column]:
    columns = []
    first_line = None
    if file_format == "csv":
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

                if observed_columns is None:
                    observed_columns = [ObservedColumn(i) for i in range(len(line))]

                if i == 0 and includes_headers:
                    first_line = line
                    continue

                for col, value in enumerate(line):
                    observed_columns[col].observe(value)

            columns = materialize_columns(observed_columns)

        if includes_headers and first_line:
            for index, col in enumerate(columns):
                col.name = first_line[index]

    elif file_format == "json":
        json_object = json.load(stream)

    return columns
