import json

import maya
import pyarrow

from kit.dtypes import KustoType


class KustoTypeResolver:
    strict_bool = ["true", "false"]
    loose_bool = ["T", "True", "t", "F", "False", "f", "0", "1"] + strict_bool
    valid_year = (1970, 2100)

    @classmethod
    def from_arrow_type(cls, arrow_type: pyarrow.lib.DataType, strict: bool = True):
        if pyarrow.types.is_binary(arrow_type):
            return KustoType.BOOL
        elif (
            pyarrow.types.is_int8(arrow_type)
            or pyarrow.types.is_int16(arrow_type)
            or pyarrow.types.is_int32(arrow_type)
        ):
            return KustoType.INT
        elif pyarrow.types.is_int64(arrow_type):
            return KustoType.LONG
        elif pyarrow.types.is_float16(arrow_type) or pyarrow.types.is_float32(arrow_type):
            return KustoType.REAL
        elif pyarrow.types.is_float64(arrow_type):
            return KustoType.DECIMAL
        elif pyarrow.types.is_date(arrow_type):
            return KustoType.DATETIME
        # elif pyarrow.dtypes.is_time(arrow_type):
        #     return KustoType.TIMESPAN
        elif (
            pyarrow.types.is_map(arrow_type) or pyarrow.types.is_nested(arrow_type) or pyarrow.types.is_list(arrow_type)
        ):
            return KustoType.DYNAMIC
        else:
            return KustoType.STRING

    @classmethod
    def from_python_type(cls, value, strict: bool = True):
        evaluated_type = type(value)

        if evaluated_type is str:
            try:
                if cls.valid_year[0] < maya.parse(value).year < cls.valid_year[1]:
                    return KustoType.DATETIME
            except:
                pass
            if not strict:
                try:
                    json.loads(value)
                    return KustoType.DYNAMIC
                except:
                    pass

        if evaluated_type is int:
            # if not strict:
            try:
                length_in_plausible_epochtime = 8 <= len(str(evaluated_type // 1)) <= 11
                if length_in_plausible_epochtime and cls.valid_year[0] < maya.MayaDT(value).year < cls.valid_year[1]:
                    return KustoType.DATETIME
            except:
                pass
            if value > 2 ** 31 or value < -1 * (2 ** 31):
                return KustoType.LONG
            return KustoType.INT
        if evaluated_type is float:
            # TODO: need to handle decimal properly
            return KustoType.REAL
        if evaluated_type in [dict, list, tuple, set]:
            return KustoType.DYNAMIC

        return KustoType.STRING

    @classmethod
    def from_string(cls, string: str, strict: bool = True):
        # TODO: missing timespan / GUID handling as well
        if type(string) is not str:
            raise ValueError("Expected a string")

        try:
            """Simple dtypes are handled here: string, int, float"""
            evaluated = eval(string)

            return KustoTypeResolver.from_python_type(evaluated, strict)
        except:
            """Special dtypes fall here: bool, datetime, timespan"""
            bool_values = cls.strict_bool if strict else cls.loose_bool

            if string in bool_values:
                return KustoType.BOOL

            # if not strict:
            try:
                if cls.valid_year[0] < maya.parse(evaluated).year < cls.valid_year[1]:
                    return KustoType.DATETIME
            except:
                pass

        return KustoType.STRING
