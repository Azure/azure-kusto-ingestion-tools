from __future__ import annotations

import json
from dataclasses import dataclass, asdict

import dacite


@dataclass
class SerializableModel:
    @classmethod
    def copy(cls, other):
        return dacite.from_dict(cls, asdict(other))

    @classmethod
    def load(cls, file):
        with open(file, 'r') as f:
            data = json.load(f)

        return dacite.from_dict(cls, data)

    @classmethod
    def from_dict(cls, data):
        return dacite.from_dict(cls, data)

    def to_json(self):
        return json.dumps(asdict(self))
