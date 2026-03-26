"""Result objects returned from completed NextGenPB runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .io.logs import ParsedLog, parse_log


@dataclass
class PotentialSampleSet:
    """Sampled electrostatic potentials paired with 3D coordinates."""

    coordinates: list[list[float]] = field(default_factory=list)
    potentials: list[float] = field(default_factory=list)


@dataclass
class NgpbResult:
    """Structured output, parsed logs, and provenance from a solver run."""

    run_id: str
    scratch_dir: Path
    workdir: Path
    kept_files: bool
    command: list[str]
    stdout_path: Path
    stderr_path: Path
    output_paths: list[Path] = field(default_factory=list)
    parsed_outputs: dict[str, PotentialSampleSet] = field(default_factory=dict)
    log: ParsedLog = field(default_factory=ParsedLog)
    metrics: dict[str, float] = field(default_factory=dict)
    log_excerpt: str | None = None
    provenance: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_logs(
        cls,
        run_id: str,
        scratch_dir: Path,
        workdir: Path,
        kept_files: bool,
        command: list[str],
        stdout_path: Path,
        stderr_path: Path,
        output_paths: list[Path],
        provenance: dict[str, str],
        excerpt_lines: int = 80,
    ) -> NgpbResult:
        """Construct a result object from solver log and output files."""
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


_PARSED_OUTPUT_FILENAMES = {"phi_surf.txt", "phi_nodes.txt", "phi_on_atoms.txt"}


def _parse_known_output_files(output_paths: list[Path]) -> dict[str, PotentialSampleSet]:
    """Parse supported solver output files into structured sample sets."""
    parsed_outputs: dict[str, PotentialSampleSet] = {}

    for path in output_paths:
        if path.name not in _PARSED_OUTPUT_FILENAMES or not path.is_file():
            continue
        parsed_outputs[path.name] = _parse_float_values(path)

    return parsed_outputs


def _parse_float_values(path: Path) -> PotentialSampleSet:
    """Parse a whitespace-delimited `x y z value` output file."""
    coordinates: list[list[float]] = []
    potentials: list[float] = []

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
