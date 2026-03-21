from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .io.logs import (
    BoxBounds,
    DomainInfo,
    ElectrostaticEnergy,
    GridBuildInfo,
    GridSubdivisions,
    ParsedLog,
    SolverInfo,
    SurfaceBuildInfo,
    SystemInfo,
    AxisBounds,
    parse_log,
)


@dataclass
class PotentialSampleSet:
    coordinates: List[List[float]] = field(default_factory=list)
    potentials: List[float] = field(default_factory=list)


@dataclass
class NgpbResult:
    run_id: str
    scratch_dir: Path
    workdir: Path
    kept_files: bool
    command: List[str]
    stdout_path: Path
    stderr_path: Path
    output_paths: List[Path] = field(default_factory=list)
    parsed_outputs: Dict[str, PotentialSampleSet] = field(default_factory=dict)
    log: ParsedLog = field(default_factory=ParsedLog)
    metrics: Dict[str, float] = field(default_factory=dict)
    log_excerpt: Optional[str] = None
    provenance: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_logs(
        cls,
        run_id: str,
        scratch_dir: Path,
        workdir: Path,
        kept_files: bool,
        command: List[str],
        stdout_path: Path,
        stderr_path: Path,
        output_paths: List[Path],
        provenance: Dict[str, str],
        excerpt_lines: int = 80,
    ) -> "NgpbResult":
        stdout_text = stdout_path.read_text(errors="replace") if stdout_path.exists() else ""
        parsed_log = parse_log(stdout_text)
        excerpt = "\n".join(stdout_text.splitlines()[-excerpt_lines:]) if stdout_text else None
        return cls(
            run_id=run_id,
            scratch_dir=scratch_dir,
            workdir=workdir,
            kept_files=kept_files,
            command=command,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            output_paths=output_paths,
            parsed_outputs=_parse_known_output_files(output_paths),
            log=parsed_log,
            metrics=parsed_log.to_metrics(),
            log_excerpt=excerpt,
            provenance=provenance,
        )


_PARSED_OUTPUT_FILENAMES = {
    "phi_surf.txt",
    "phi_nodes.txt",
    "phi_on_atoms.txt",
}


def _parse_known_output_files(output_paths: List[Path]) -> Dict[str, List[float]]:
    parsed_outputs: Dict[str, PotentialSampleSet] = {}

    for path in output_paths:
        if path.name not in _PARSED_OUTPUT_FILENAMES or not path.is_file():
            continue
        parsed_outputs[path.name] = _parse_float_values(path)

    return parsed_outputs


def _parse_float_values(path: Path) -> PotentialSampleSet:
    coordinates: List[List[float]] = []
    potentials: List[float] = []

    for line in path.read_text(errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            values = [float(token) for token in stripped.split()]
        except ValueError:
            # Skip non-numeric rows such as comments or headers.
            continue
        if len(values) != 4:
            continue
        coordinates.append(values[:3])
        potentials.append(values[3])

    return PotentialSampleSet(coordinates=coordinates, potentials=potentials)
