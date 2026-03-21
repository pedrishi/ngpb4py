from __future__ import annotations

import re
from dataclasses import dataclass, field

_FLOAT_RE = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"
_HEADER_RE = re.compile(r"=+\s*\[\s*(.*?)\s*\]\s*=+")
_SELECTED_FILE_RE = re.compile(r"Selected\s+(.+?)\s*:\s*(.+)")
_VECTOR_RE = re.compile(
    r"\[\s*(" + _FLOAT_RE + r")\s*,\s*(" + _FLOAT_RE + r")\s*,\s*(" + _FLOAT_RE + r")\s*\]"
)
_RANGE_RE = re.compile(r"=\s*\[\s*(" + _FLOAT_RE + r")\s*,\s*(" + _FLOAT_RE + r")\s*\]")
_NX_NY_NZ_RE = re.compile(r"nx\s*=\s*(\d+)\s+ny\s*=\s*(\d+)\s+nz\s*=\s*(\d+)", re.IGNORECASE)
_ITERATION_RE = re.compile(r"iteration:\s*(\d+)", re.IGNORECASE)
_RANK_RE = re.compile(r"\[Rank\s+(\d+)\]", re.IGNORECASE)
_STATUS_OK_RE = re.compile(r"\bok!?$", re.IGNORECASE)
_FIELD_NUMBER_RE = re.compile(r":\s*(" + _FLOAT_RE + r")(?:\s+\[[^\]]+\])?\s*$")


@dataclass(frozen=True)
class AxisBounds:
    minimum: float
    maximum: float


@dataclass(frozen=True)
class BoxBounds:
    x: AxisBounds
    y: AxisBounds
    z: AxisBounds


@dataclass(frozen=True)
class GridSubdivisions:
    nx: int
    ny: int
    nz: int


@dataclass
class SystemInfo:
    parameters_file: str | None = None
    pqr_file: str | None = None
    number_of_atoms: int | None = None
    protein_size_angstrom: tuple[float, float, float] | None = None
    solute_dielectric_constant: float | None = None
    solvent_dielectric_constant: float | None = None
    temperature_kelvin: float | None = None
    ionic_strength_mol_per_l: float | None = None


@dataclass
class DomainInfo:
    scale: float | None = None
    center_of_system_angstrom: tuple[float, float, float] | None = None
    perfil_outer_box: float | None = None
    complete_domain_box: BoxBounds | None = None
    perfil_uniform_grid: float | None = None
    uniform_grid_box: BoxBounds | None = None
    uniform_grid_subdivisions: GridSubdivisions | None = None


@dataclass
class SurfaceBuildInfo:
    cavity_detection_time_s: float | None = None
    completed: bool | None = None


@dataclass
class GridBuildInfo:
    total_nodes: int | None = None
    total_quadrants: int | None = None
    rank_count: int | None = None


@dataclass
class SolverInfo:
    boundary_conditions: str | None = None
    rho_calculation_time_ms: float | None = None
    initial_vector: str | None = None
    precision: str | None = None
    linear_solver: str | None = None
    preconditioner: str | None = None
    convergence_condition: str | None = None
    final_status: str | None = None
    iteration_count: int | None = None


@dataclass
class ElectrostaticEnergy:
    net_charge_e: float | None = None
    flux_charge_e: float | None = None
    polarization_energy_kt: float | None = None
    direct_ionic_energy_kt: float | None = None
    coulombic_energy_kt: float | None = None
    total_electrostatic_energy_kt: float | None = None


@dataclass
class ParsedLog:
    system: SystemInfo | None = None
    domain: DomainInfo | None = None
    surface: SurfaceBuildInfo | None = None
    grid: GridBuildInfo | None = None
    solver: SolverInfo | None = None
    energies: ElectrostaticEnergy | None = None
    preamble_text: str | None = None
    section_text: dict[str, str] = field(default_factory=dict)

    def section_count(self) -> int:
        return sum(
            section is not None
            for section in (
                self.system,
                self.domain,
                self.surface,
                self.grid,
                self.solver,
                self.energies,
            )
        )

    def to_metrics(self) -> dict[str, float]:
        metrics: dict[str, float] = {}
        if self.grid is not None:
            if self.grid.total_quadrants is not None:
                metrics["mesh.elements"] = float(self.grid.total_quadrants)
            if self.grid.total_nodes is not None:
                metrics["mesh.nodes"] = float(self.grid.total_nodes)
        if self.solver is not None and self.solver.iteration_count is not None:
            metrics["solver.iterations"] = float(self.solver.iteration_count)
        if self.energies is not None:
            if self.energies.total_electrostatic_energy_kt is not None:
                metrics["energy.total"] = self.energies.total_electrostatic_energy_kt
            if self.energies.polarization_energy_kt is not None:
                metrics["energy.solvation"] = self.energies.polarization_energy_kt
            if self.energies.coulombic_energy_kt is not None:
                metrics["energy.coulombic"] = self.energies.coulombic_energy_kt
            if self.energies.direct_ionic_energy_kt is not None:
                metrics["energy.direct_ionic"] = self.energies.direct_ionic_energy_kt
        return metrics


def parse_log(text: str) -> ParsedLog:
    preamble_lines, sections = _split_sections(text)
    selected_files = _parse_selected_files(preamble_lines)

    parsed = ParsedLog(
        preamble_text="\n".join(preamble_lines).strip() or None,
        section_text={name: "\n".join(lines).strip() for name, lines in sections.items()},
    )

    if "system" in sections:
        parsed.system = _parse_system_info(sections["system"], selected_files)
    elif selected_files:
        parsed.system = SystemInfo(
            parameters_file=selected_files.get("parameters_file"),
            pqr_file=selected_files.get("pqr_file"),
        )

    if "domain" in sections:
        parsed.domain = _parse_domain_info(sections["domain"])
    if "surface" in sections:
        parsed.surface = _parse_surface_info(sections["surface"])
    if "grid" in sections:
        parsed.grid = _parse_grid_info(sections["grid"])
    if "solver" in sections:
        parsed.solver = _parse_solver_info(sections["solver"])
    if "energies" in sections:
        parsed.energies = _parse_energy_info(sections["energies"])

    return parsed


def parse_log_metrics(text: str) -> dict[str, float]:
    return parse_log(text).to_metrics()


def _split_sections(text: str) -> tuple[list[str], dict[str, list[str]]]:
    preamble: list[str] = []
    sections: dict[str, list[str]] = {}
    current_name: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        header_match = _HEADER_RE.search(line.strip())
        if header_match:
            current_name = _normalize_section_name(header_match.group(1))
            if current_name is not None:
                sections.setdefault(current_name, [])
            else:
                current_name = None
            continue

        if _is_separator_line(line):
            continue

        if current_name is None:
            preamble.append(line)
        else:
            sections[current_name].append(line)

    return preamble, sections


def _normalize_section_name(name: str) -> str | None:
    normalized = re.sub(r"\s+", " ", name.strip().lower())
    mapping = {
        "system information": "system",
        "domain information": "domain",
        "building surface with nanoshaper": "surface",
        "building grid": "grid",
        "starting numerical solution using lis": "solver",
        "electrostatic energy": "energies",
    }
    return mapping.get(normalized)


def _is_separator_line(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and set(stripped) <= {"="}


def _parse_selected_files(lines: list[str]) -> dict[str, str]:
    selected: dict[str, str] = {}
    for line in lines:
        match = _SELECTED_FILE_RE.search(line.strip())
        if not match:
            continue
        label = match.group(1).strip().lower()
        value = match.group(2).strip()
        if "parameters file" in label:
            selected["parameters_file"] = value
        elif "pqr file" in label:
            selected["pqr_file"] = value
    return selected


def _parse_system_info(lines: list[str], selected_files: dict[str, str]) -> SystemInfo:
    info = SystemInfo(
        parameters_file=selected_files.get("parameters_file"),
        pqr_file=selected_files.get("pqr_file"),
    )
    dielectric_values: list[float] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Number of atoms"):
            info.number_of_atoms = _parse_int_field(line)
        elif line.startswith("Size protein"):
            info.protein_size_angstrom = _parse_vector(line)
        elif "epsilon" in line.lower():
            value = _parse_float_field(line)
            if value is not None:
                dielectric_values.append(value)
                lower = line.lower()
                if "molecular" in lower or "solute" in lower or "protein" in lower:
                    info.solute_dielectric_constant = value
                elif (
                    "solvent" in lower
                    and info.solvent_dielectric_constant is None
                    and len(dielectric_values) > 1
                ):
                    info.solvent_dielectric_constant = value
        elif line.startswith("Temperature"):
            info.temperature_kelvin = _parse_float_field(line)
        elif line.startswith("Ionic strength"):
            info.ionic_strength_mol_per_l = _parse_float_field(line)

    if info.solute_dielectric_constant is None and dielectric_values:
        info.solute_dielectric_constant = dielectric_values[0]
    if info.solvent_dielectric_constant is None and len(dielectric_values) >= 2:
        info.solvent_dielectric_constant = dielectric_values[1]

    return info


def _parse_domain_info(lines: list[str]) -> DomainInfo:
    info = DomainInfo()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith("Scale"):
            info.scale = _parse_float_field(line)
        elif line.startswith("Center of the System"):
            info.center_of_system_angstrom = _parse_vector(line)
        elif line.startswith("Perfil outer box"):
            info.perfil_outer_box = _parse_float_field(line)
        elif line.startswith("Complete Domain Box Size"):
            info.complete_domain_box = _parse_box(lines[index + 1 : index + 4])
            index += 3
        elif line.startswith("Perfil uniform grid"):
            info.perfil_uniform_grid = _parse_float_field(line)
        elif line.startswith("Uniform grid Size"):
            info.uniform_grid_box = _parse_box(lines[index + 1 : index + 4])
            index += 3
        elif "Number of Subdivisions" in line:
            info.uniform_grid_subdivisions = _parse_subdivisions(line)
        index += 1
    return info


def _parse_surface_info(lines: list[str]) -> SurfaceBuildInfo:
    cavity_detection_time_s: float | None = None
    completed: bool | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if "Cavity detection time" in line:
            cavity_detection_time_s = _parse_float_from_text(line)
        if _STATUS_OK_RE.search(line) or "Unpacking rays packet" in line:
            completed = True

    return SurfaceBuildInfo(cavity_detection_time_s=cavity_detection_time_s, completed=completed)


def _parse_grid_info(lines: list[str]) -> GridBuildInfo:
    total_nodes: int | None = None
    total_quadrants: int | None = None
    ranks = set()

    for raw_line in lines:
        line = raw_line.strip()
        rank_match = _RANK_RE.search(line)
        if rank_match:
            ranks.add(int(rank_match.group(1)))
        if "[Global] Total nodes" in line:
            total_nodes = _parse_int_field(line)
        elif "[Global] Total quadrants" in line:
            total_quadrants = _parse_int_field(line)

    return GridBuildInfo(
        total_nodes=total_nodes,
        total_quadrants=total_quadrants,
        rank_count=len(ranks) if ranks else None,
    )


def _parse_solver_info(lines: list[str]) -> SolverInfo:
    info = SolverInfo()

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Selected BCs"):
            info.boundary_conditions = _parse_text_field(line)
        elif line.startswith("Time to calculate rho"):
            info.rho_calculation_time_ms = _parse_float_from_text(line)
        elif line.startswith("initial vector x"):
            info.initial_vector = _parse_text_field(line)
        elif line.startswith("precision"):
            info.precision = _parse_text_field(line)
        elif line.startswith("linear solver status"):
            info.final_status = _parse_text_field(line)
        elif line.startswith("linear solver"):
            info.linear_solver = _parse_text_field(line)
        elif line.startswith("preconditioner"):
            info.preconditioner = _parse_text_field(line)
        elif line.startswith("convergence condition"):
            info.convergence_condition = _parse_text_field(line)
        else:
            iteration_match = _ITERATION_RE.search(line)
            if iteration_match:
                info.iteration_count = int(iteration_match.group(1))

    return info


def _parse_energy_info(lines: list[str]) -> ElectrostaticEnergy:
    info = ElectrostaticEnergy()

    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("Net charge"):
            info.net_charge_e = _parse_float_field(line)
        elif line.startswith("Flux charge"):
            info.flux_charge_e = _parse_float_field(line)
        elif line.startswith("Polarization energy"):
            info.polarization_energy_kt = _parse_float_field(line)
        elif line.startswith("Direct ionic energy"):
            info.direct_ionic_energy_kt = _parse_float_field(line)
        elif line.startswith("Coulombic energy"):
            info.coulombic_energy_kt = _parse_float_field(line)
        elif line.startswith("Sum of electrostatic energy contributions"):
            info.total_electrostatic_energy_kt = _parse_float_field(line)

    return info


def _parse_vector(line: str) -> tuple[float, float, float] | None:
    match = _VECTOR_RE.search(line)
    if not match:
        return None
    return (float(match.group(1)), float(match.group(2)), float(match.group(3)))


def _parse_box(lines: list[str]) -> BoxBounds | None:
    if len(lines) < 3:
        return None
    axes: dict[str, AxisBounds] = {}
    for raw_line in lines[:3]:
        line = raw_line.strip()
        if not line:
            continue
        axis = line[0].lower()
        match = _RANGE_RE.search(line)
        if axis not in {"x", "y", "z"} or not match:
            continue
        axes[axis] = AxisBounds(float(match.group(1)), float(match.group(2)))
    if len(axes) != 3:
        return None
    return BoxBounds(x=axes["x"], y=axes["y"], z=axes["z"])


def _parse_subdivisions(line: str) -> GridSubdivisions | None:
    match = _NX_NY_NZ_RE.search(line)
    if not match:
        return None
    return GridSubdivisions(nx=int(match.group(1)), ny=int(match.group(2)), nz=int(match.group(3)))


def _parse_int_field(line: str) -> int | None:
    value = _parse_float_field(line)
    return int(value) if value is not None else None


def _parse_float_field(line: str) -> float | None:
    match = _FIELD_NUMBER_RE.search(line)
    if not match:
        return None
    return float(match.group(1))


def _parse_float_from_text(line: str) -> float | None:
    match = re.search(_FLOAT_RE, line)
    return float(match.group(0)) if match else None


def _parse_text_field(line: str) -> str | None:
    if ":" not in line:
        return None
    value = line.split(":", 1)[1].strip()
    return value or None
