from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .io.prm import load_prm, render_prm

_UNSET = object()


@dataclass(frozen=True)
class PrmOption:
    name: str
    default: Any
    value_type: type
    block: str | None = None
    choices: frozenset[Any] | None = None
    unit: str | None = None
    description: str | None = None

    @property
    def has_default(self) -> bool:
        return self.default is not _UNSET


_DEFAULT_SCHEMA: dict[str, PrmOption] = {
    "filetype": PrmOption(
        name="filetype",
        default="pqr",
        value_type=str,
        block="input",
        choices=frozenset({"pdb", "pqr"}),
        description="Structure file type",
    ),
    "filename": PrmOption(
        name="filename",
        default="input.pqr",
        value_type=str,
        block="input",
        description="Structure file path",
    ),
    "radius_file": PrmOption(
        name="radius_file",
        default="radius.siz",
        value_type=str,
        block="input",
        description="Radius file path",
    ),
    "charge_file": PrmOption(
        name="charge_file",
        default="charge.crg",
        value_type=str,
        block="input",
        description="Charge file path",
    ),
    "write_pqr": PrmOption(
        name="write_pqr",
        default=0,
        value_type=int,
        block="input",
        choices=frozenset({0, 1}),
        description="Whether to write a processed .pqr file",
    ),
    "name_pqr": PrmOption(
        name="name_pqr",
        default="output.pqr",
        value_type=str,
        block="input",
        description="Output .pqr filename",
    ),
    "mesh_shape": PrmOption(
        name="mesh_shape",
        default=0,
        value_type=int,
        block="mesh",
        choices=frozenset({0, 1, 2, 3}),
        description="Mesh shape configuration",
    ),
    "perfil1": PrmOption(
        name="perfil1",
        default=0.8,
        value_type=float,
        block="mesh",
        description="Core mesh spacing ratio",
    ),
    "perfil2": PrmOption(
        name="perfil2",
        default=0.2,
        value_type=float,
        block="mesh",
        description="Outer mesh spacing ratio",
    ),
    "scale": PrmOption(
        name="scale", default=2.0, value_type=float, block="mesh", description="Core scale"
    ),
    "rand_center": PrmOption(
        name="rand_center",
        default=0,
        value_type=int,
        block="mesh",
        choices=frozenset({0, 1}),
        description="Whether to randomly shift the mesh center",
    ),
    "cx_foc": PrmOption(name="cx_foc", default=0.0, value_type=float, block="mesh"),
    "cy_foc": PrmOption(name="cy_foc", default=0.0, value_type=float, block="mesh"),
    "cz_foc": PrmOption(name="cz_foc", default=0.0, value_type=float, block="mesh"),
    "n_grid": PrmOption(name="n_grid", default=10, value_type=int, block="mesh"),
    "unilevel": PrmOption(name="unilevel", default=6, value_type=int, block="mesh"),
    "outlevel": PrmOption(name="outlevel", default=1, value_type=int, block="mesh"),
    "x1": PrmOption(name="x1", default=_UNSET, value_type=float, block="mesh"),
    "x2": PrmOption(name="x2", default=_UNSET, value_type=float, block="mesh"),
    "y1": PrmOption(name="y1", default=_UNSET, value_type=float, block="mesh"),
    "y2": PrmOption(name="y2", default=_UNSET, value_type=float, block="mesh"),
    "z1": PrmOption(name="z1", default=_UNSET, value_type=float, block="mesh"),
    "z2": PrmOption(name="z2", default=_UNSET, value_type=float, block="mesh"),
    "refine_box": PrmOption(
        name="refine_box", default=0, value_type=int, block="mesh", choices=frozenset({0, 1})
    ),
    "outrefine_x1": PrmOption(name="outrefine_x1", default=-4.0, value_type=float, block="mesh"),
    "outrefine_x2": PrmOption(name="outrefine_x2", default=4.0, value_type=float, block="mesh"),
    "outrefine_y1": PrmOption(name="outrefine_y1", default=-4.0, value_type=float, block="mesh"),
    "outrefine_y2": PrmOption(name="outrefine_y2", default=4.0, value_type=float, block="mesh"),
    "outrefine_z1": PrmOption(name="outrefine_z1", default=-4.0, value_type=float, block="mesh"),
    "outrefine_z2": PrmOption(name="outrefine_z2", default=4.0, value_type=float, block="mesh"),
    "linearized": PrmOption(
        name="linearized", default=1, value_type=int, block="model", choices=frozenset({1})
    ),
    "bc_type": PrmOption(
        name="bc_type", default=1, value_type=int, block="model", choices=frozenset({0, 1, 2})
    ),
    "molecular_dielectric_constant": PrmOption(
        name="molecular_dielectric_constant", default=2.0, value_type=float, block="model"
    ),
    "solvent_dielectric_constant": PrmOption(
        name="solvent_dielectric_constant", default=80.0, value_type=float, block="model"
    ),
    "ionic_strength": PrmOption(
        name="ionic_strength", default=0.145, value_type=float, block="model"
    ),
    "T": PrmOption(name="T", default=298.15, value_type=float, block="model", unit="K"),
    "calc_energy": PrmOption(
        name="calc_energy", default=2, value_type=int, block="model", choices=frozenset({0, 1, 2})
    ),
    "calc_coulombic": PrmOption(
        name="calc_coulombic", default=0, value_type=int, block="model", choices=frozenset({0, 1})
    ),
    "atoms_write": PrmOption(
        name="atoms_write", default=0, value_type=int, block="model", choices=frozenset({0, 1})
    ),
    "map_type": PrmOption(name="map_type", default="vtu", value_type=str, block="model"),
    "potential_map": PrmOption(
        name="potential_map", default=0, value_type=int, block="model", choices=frozenset({0, 1})
    ),
    "surf_write": PrmOption(
        name="surf_write", default=0, value_type=int, block="model", choices=frozenset({0, 1})
    ),
    "surface_type": PrmOption(
        name="surface_type",
        default=_UNSET,
        value_type=int,
        block="surface",
        choices=frozenset({0, 1}),
    ),
    "surface_parameter": PrmOption(
        name="surface_parameter", default=_UNSET, value_type=float, block="surface"
    ),
    "stern_layer_surf": PrmOption(
        name="stern_layer_surf",
        default=0,
        value_type=int,
        block="surface",
        choices=frozenset({0, 1}),
    ),
    "stern_layer_thickness": PrmOption(
        name="stern_layer_thickness", default=2.0, value_type=float, block="surface", unit="A"
    ),
    "number_of_threads": PrmOption(
        name="number_of_threads", default=1, value_type=int, block="surface"
    ),
    "linear_solver": PrmOption(
        name="linear_solver",
        default="lis",
        value_type=str,
        block="solver",
        choices=frozenset({"lis", "mumps"}),
    ),
    "solver_options": PrmOption(
        name="solver_options", default=_UNSET, value_type=str, block="solver"
    ),
}


_INPUT_FILE_KEYS = ("filename", "radius_file", "charge_file")


@dataclass
class NgpbConfig:
    data: dict[str, Any] = field(default_factory=dict)
    schema: dict[str, PrmOption] = field(default_factory=lambda: dict(_DEFAULT_SCHEMA))
    source_prm_path: Path | None = None
    source_dir: Path | None = None

    @classmethod
    def defaults(cls) -> NgpbConfig:
        data = {
            name: option.default for name, option in _DEFAULT_SCHEMA.items() if option.has_default
        }
        return cls(data=data)

    @classmethod
    def from_prm(cls, prm_path: str, schema: dict[str, PrmOption] | None = None) -> NgpbConfig:
        resolved_path = Path(prm_path).resolve()
        loaded = load_prm(str(resolved_path))
        return cls(
            data=loaded,
            schema=dict(schema) if schema else dict(_DEFAULT_SCHEMA),
            source_prm_path=resolved_path,
            source_dir=resolved_path.parent,
        )

    def with_updates(self, updates: Mapping[str, Any]) -> NgpbConfig:
        merged = dict(self.data)
        merged.update(updates)
        return NgpbConfig(
            data=merged,
            schema=dict(self.schema),
            source_prm_path=self.source_prm_path,
            source_dir=self.source_dir,
        )

    def validate(self) -> None:
        for key, option in self.schema.items():
            if key not in self.data:
                continue
            value = self.data[key]
            if value is None:
                continue
            if option.value_type is float and isinstance(value, int):
                pass
            elif not isinstance(value, option.value_type):
                raise TypeError(
                    f"{key} expects {option.value_type.__name__}, got {type(value).__name__}"
                )
            if option.choices is not None and value not in option.choices:
                allowed = ", ".join(str(choice) for choice in sorted(option.choices, key=str))
                raise ValueError(f"{key} expects one of {{{allowed}}}, got {value!r}")

    def to_prm(self) -> str:
        self.validate()
        return render_prm(self.data, self.schema)

    def iter_items(self) -> Iterable[tuple[str, Any]]:
        return self.data.items()

    def prm_filename(self) -> str:
        if self.source_prm_path is not None:
            return self.source_prm_path.name
        return "ngpb.prm"

    def iter_input_file_keys(self) -> Iterable[str]:
        for key in _INPUT_FILE_KEYS:
            if self.data.get(key) is not None:
                yield key

    def resolve_input_file(self, key: str) -> Path:
        value = self.data.get(key)
        if value is None:
            raise KeyError(key)
        if isinstance(value, Path):
            return value.resolve()

        candidate = Path(str(value)).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()
        if self.source_dir is not None:
            return (self.source_dir / candidate).resolve()
        raise FileNotFoundError(
            f"Cannot resolve input file for '{key}' from value '{value}' without a source directory"
        )
