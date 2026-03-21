from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Dict, List, Optional, Tuple


_FLOAT_RE = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"
_HEADER_RE = re.compile(r"=+\s*\[\s*(.*?)\s*\]\s*=+")
_SELECTED_FILE_RE = re.compile(r"Selected\s+(.+?)\s*:\s*(.+)")
_VECTOR_RE = re.compile(r"\[\s*(" + _FLOAT_RE + r")\s*,\s*(" + _FLOAT_RE + r")\s*,\s*(" + _FLOAT_RE + r")\s*\]")
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
    parameters_file: Optional[str] = None
    pqr_file: Optional[str] = None
    number_of_atoms: Optional[int] = None
    protein_size_angstrom: Optional[Tuple[float, float, float]] = None
    solute_dielectric_constant: Optional[float] = None
    solvent_dielectric_constant: Optional[float] = None
    temperature_kelvin: Optional[float] = None
    ionic_strength_mol_per_l: Optional[float] = None


@dataclass
class DomainInfo:
    scale: Optional[float] = None
    center_of_system_angstrom: Optional[Tuple[float, float, float]] = None
    perfil_outer_box: Optional[float] = None
    complete_domain_box: Optional[BoxBounds] = None
    perfil_uniform_grid: Optional[float] = None
    uniform_grid_box: Optional[BoxBounds] = None
    uniform_grid_subdivisions: Optional[GridSubdivisions] = None


@dataclass
class SurfaceBuildInfo:
    cavity_detection_time_s: Optional[float] = None
    completed: Optional[bool] = None


@dataclass
class GridBuildInfo:
    total_nodes: Optional[int] = None
    total_quadrants: Optional[int] = None
    rank_count: Optional[int] = None


@dataclass
class SolverInfo:
    boundary_conditions: Optional[str] = None
    rho_calculation_time_ms: Optional[float] = None
    initial_vector: Optional[str] = None
    precision: Optional[str] = None
    linear_solver: Optional[str] = None
    preconditioner: Optional[str] = None
    convergence_condition: Optional[str] = None
    final_status: Optional[str] = None
    iteration_count: Optional[int] = None


@dataclass
class ElectrostaticEnergy:
    net_charge_e: Optional[float] = None
    flux_charge_e: Optional[float] = None
    polarization_energy_kt: Optional[float] = None
    direct_ionic_energy_kt: Optional[float] = None
    coulombic_energy_kt: Optional[float] = None
    total_electrostatic_energy_kt: Optional[float] = None


@dataclass
class ParsedLog:
    system: Optional[SystemInfo] = None
    domain: Optional[DomainInfo] = None
    surface: Optional[SurfaceBuildInfo] = None
    grid: Optional[GridBuildInfo] = None
    solver: Optional[SolverInfo] = None
    energies: Optional[ElectrostaticEnergy] = None
    preamble_text: Optional[str] = None
    section_text: Dict[str, str] = field(default_factory=dict)

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

    def to_metrics(self) -> Dict[str, float]:
        metrics: Dict[str, float] = {}
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


def parse_log_metrics(text: str) -> Dict[str, float]:
    return parse_log(text).to_metrics()


def _split_sections(text: str) -> Tuple[List[str], Dict[str, List[str]]]:
    preamble: List[str] = []
    sections: Dict[str, List[str]] = {}
    current_name: Optional[str] = None

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


def _normalize_section_name(name: str) -> Optional[str]:
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


def _parse_selected_files(lines: List[str]) -> Dict[str, str]:
    selected: Dict[str, str] = {}
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


def _parse_system_info(lines: List[str], selected_files: Dict[str, str]) -> SystemInfo:
    info = SystemInfo(
        parameters_file=selected_files.get("parameters_file"),
        pqr_file=selected_files.get("pqr_file"),
    )
    dielectric_values: List[float] = []

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
                elif "solvent" in lower and info.solvent_dielectric_constant is None and len(dielectric_values) > 1:
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


def _parse_domain_info(lines: List[str]) -> DomainInfo:
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


def _parse_surface_info(lines: List[str]) -> SurfaceBuildInfo:
    cavity_detection_time_s: Optional[float] = None
    completed: Optional[bool] = None

    for raw_line in lines:
        line = raw_line.strip()
        if "Cavity detection time" in line:
            cavity_detection_time_s = _parse_float_from_text(line)
        if _STATUS_OK_RE.search(line) or "Unpacking rays packet" in line:
            completed = True

    return SurfaceBuildInfo(
        cavity_detection_time_s=cavity_detection_time_s,
        completed=completed,
    )


def _parse_grid_info(lines: List[str]) -> GridBuildInfo:
    total_nodes: Optional[int] = None
    total_quadrants: Optional[int] = None
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


def _parse_solver_info(lines: List[str]) -> SolverInfo:
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


def _parse_energy_info(lines: List[str]) -> ElectrostaticEnergy:
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


def _parse_vector(line: str) -> Optional[Tuple[float, float, float]]:
    match = _VECTOR_RE.search(line)
    if not match:
        return None
    return (float(match.group(1)), float(match.group(2)), float(match.group(3)))


def _parse_box(lines: List[str]) -> Optional[BoxBounds]:
    if len(lines) < 3:
        return None
    axes: Dict[str, AxisBounds] = {}
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


def _parse_subdivisions(line: str) -> Optional[GridSubdivisions]:
    match = _NX_NY_NZ_RE.search(line)
    if not match:
        return None
    return GridSubdivisions(nx=int(match.group(1)), ny=int(match.group(2)), nz=int(match.group(3)))


def _parse_int_field(line: str) -> Optional[int]:
    value = _parse_float_field(line)
    return int(value) if value is not None else None


def _parse_float_field(line: str) -> Optional[float]:
    match = _FIELD_NUMBER_RE.search(line)
    if not match:
        return None
    return float(match.group(1))


def _parse_float_from_text(line: str) -> Optional[float]:
    match = re.search(_FLOAT_RE, line)
    return float(match.group(0)) if match else None


def _parse_text_field(line: str) -> Optional[str]:
    if ":" not in line:
        return None
    value = line.split(":", 1)[1].strip()
    return value or None
