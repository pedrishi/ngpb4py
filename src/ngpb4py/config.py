from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from .io.prm import load_prm, render_prm


@dataclass(frozen=True)
class PrmOption:
    name: str
    default: Any
    value_type: type
    unit: str | None = None
    description: str | None = None


_DEFAULT_SCHEMA: dict[str, PrmOption] = {
    "solver.max_iterations": PrmOption(
        name="solver.max_iterations",
        default=200,
        value_type=int,
        description="Maximum solver iterations",
    ),
    "solver.tolerance": PrmOption(
        name="solver.tolerance",
        default=1e-6,
        value_type=float,
        description="Solver convergence tolerance",
    ),
    "mesh.fineness": PrmOption(
        name="mesh.fineness", default=2, value_type=int, description="Mesh refinement level"
    ),
    "output.prefix": PrmOption(
        name="output.prefix", default="ngpb", value_type=str, description="Output file prefix"
    ),
}


@dataclass
class NgpbConfig:
    data: dict[str, Any] = field(default_factory=dict)
    schema: dict[str, PrmOption] = field(default_factory=lambda: dict(_DEFAULT_SCHEMA))

    @classmethod
    def defaults(cls) -> NgpbConfig:
        data = {name: option.default for name, option in _DEFAULT_SCHEMA.items()}
        return cls(data=data)

    @classmethod
    def from_prm(cls, prm_path: str, schema: dict[str, PrmOption] | None = None) -> NgpbConfig:
        loaded = load_prm(prm_path)
        return cls(data=loaded, schema=dict(schema) if schema else dict(_DEFAULT_SCHEMA))

    def with_updates(self, updates: Mapping[str, Any]) -> NgpbConfig:
        merged = dict(self.data)
        merged.update(updates)
        return NgpbConfig(data=merged, schema=dict(self.schema))

    def validate(self) -> None:
        for key, option in self.schema.items():
            if key not in self.data:
                continue
            value = self.data[key]
            if value is None:
                continue
            if not isinstance(value, option.value_type):
                raise TypeError(
                    f"{key} expects {option.value_type.__name__}, got {type(value).__name__}"
                )

    def to_prm(self) -> str:
        self.validate()
        return render_prm(self.data, self.schema)

    def iter_items(self) -> Iterable[tuple[str, Any]]:
        return self.data.items()
