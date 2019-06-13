from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
# TODO: fix this - type resolving is hacky as it requires types to be known.
#  should probably fall back to string comparison
# noinspection PyUnresolvedReferences
from typing import List, Dict

import maya
from typing_inspect import is_generic_type, get_args

from kit.helpers import to_python_name


@dataclass
class SerializableModel:
    @classmethod
    def copy(cls, other):
        return cls.fromdict(asdict(other))

    @classmethod
    def load(cls, file):
        with open(file, 'r') as f:
            data = json.load(f)

        return cls.fromdict(data)

    @classmethod
    def fromdict(cls, d) -> SerializableModel:
        # translate to PEP
        d = {to_python_name(k): v for k, v in d.items()}

        # FIXME: hacky hacky hacky (:
        from kit.models.basic import Column
        from kit.models.database import Database, Table
        from kit.models.data_source import DataSource, DataEntity, DataFile
        from kit.models.ingestion import IngestionManifest, IngestionSource, IngestionMapping, IngestionOp

        known = {Column, Database, Table, DataSource, DataEntity, DataFile, IngestionMapping, IngestionOp, IngestionSource, IngestionManifest}
        ctor_params = {}
        for field in cls.__dataclass_fields__.values():
            if d.get(field.name) is not None:
                T = eval(field.type)
                if T in [int, str, float, bool, float]:
                    # validate type
                    ctor_params[field.name] = T(d[field.name])
                elif T is datetime:
                    ctor_params[field.name] = maya.when(d[field.name]).datetime()
                elif is_generic_type(T):
                    # go deep
                    T_of = get_args(T)[0]
                    if issubclass(T_of, SerializableModel):
                        ctor_params[field.name] = [T_of.fromdict(nested_dict) for nested_dict in d[field.name]]
                    else:
                        ctor_params[field.name] = d[field.name]
                elif issubclass(T, SerializableModel):
                    ctor_params[field.name] = T_of.fromdict(d[field.name])
                else:
                    ctor_params[field.name] = d[field.name]

        return cls(**ctor_params)

    def to_json(self):
        return json.dumps(asdict(self))
