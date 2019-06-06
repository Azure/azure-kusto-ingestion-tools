from __future__ import annotations

from dataclasses import dataclass

from kit.dtypes import KustoType
from kit.models.serializable import SerializableModel


@dataclass
class Column(SerializableModel):
    dtype: str = KustoType.STRING.value
    name: str = None
    index: int = None

    def __init__(self, name: str = None, dtype: str = None, index: int = None, data_type: KustoType = None):
        self.name = name

        if name is None and index is None:
            raise ValueError("Must explicitly specify name or index")

        if data_type:
            self.dtype = data_type.value
        elif dtype:
            self.dtype = dtype
        else:
            raise ValueError("Missing data type property")
        self.index = index

    @property
    def moniker(self):
        return self.name if self.name else f"Col_{self.index}"

    @property
    def data_type(self):
        return KustoType(self.dtype)

    @data_type.setter
    def data_type(self, v: KustoType):
        self.dtype = v.value
