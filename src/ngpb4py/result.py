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
    provenance: dict[str, str] = field(default_factory=dict)
    _stdout_text: str = field(default="", repr=False)
    _output_text_by_name: dict[str, str | None] = field(default_factory=dict, repr=False)
    _excerpt_lines: int = field(default=80, repr=False)
    _log: ParsedLog | None = field(default=None, init=False, repr=False)
    _metrics: dict[str, float] | None = field(default=None, init=False, repr=False)
    _parsed_outputs: dict[str, PotentialSampleSet] | None = field(
        default=None, init=False, repr=False
    )
    _log_excerpt: str | None = field(default=None, init=False, repr=False)

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
        return cls(
            run_id=run_id,
            scratch_dir=scratch_dir,
            workdir=workdir,
            kept_files=kept_files,
            command=command,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            output_paths=output_paths,
            provenance=provenance,
            _stdout_text=stdout_text,
            _output_text_by_name=_collect_output_text_by_name(
                output_paths, cache_contents=not kept_files
            ),
            _excerpt_lines=excerpt_lines,
        )

    @property
    def log(self) -> ParsedLog:
        """Parse and cache the structured log on first access."""
        if self._log is None:
            self._log = parse_log(self._stdout_text)
        return self._log

    @property
    def metrics(self) -> dict[str, float]:
        """Compute and cache derived metrics on first access."""
        if self._metrics is None:
            self._metrics = self.log.to_metrics()
        return self._metrics

    @property
    def parsed_outputs(self) -> dict[str, PotentialSampleSet]:
        """Parse supported output files on first access."""
        if self._parsed_outputs is None:
            self._parsed_outputs = _parse_known_output_files(
                output_paths=self.output_paths, output_text_by_name=self._output_text_by_name
            )
        return self._parsed_outputs

    @property
    def log_excerpt(self) -> str | None:
        """Build and cache the tail excerpt of stdout on first access."""
        if self._log_excerpt is None and self._stdout_text:
            self._log_excerpt = "\n".join(self._stdout_text.splitlines()[-self._excerpt_lines :])
        return self._log_excerpt


_PARSED_OUTPUT_FILENAMES = {"phi_surf.txt", "phi_nodes.txt", "phi_on_atoms.txt"}


def _collect_output_text_by_name(
    output_paths: list[Path], *, cache_contents: bool
) -> dict[str, str | None]:
    output_text_by_name: dict[str, str | None] = {}

    for path in output_paths:
        if path.name not in _PARSED_OUTPUT_FILENAMES or not path.is_file():
            continue
        output_text_by_name[path.name] = (
            path.read_text(errors="replace") if cache_contents else None
        )

    return output_text_by_name


def _parse_known_output_files(
    output_paths: list[Path], output_text_by_name: dict[str, str | None]
) -> dict[str, PotentialSampleSet]:
    """Parse supported solver output files into structured sample sets."""
    parsed_outputs: dict[str, PotentialSampleSet] = {}

    for path in output_paths:
        if path.name not in _PARSED_OUTPUT_FILENAMES:
            continue
        text = output_text_by_name.get(path.name)
        if text is None:
            if not path.is_file():
                continue
            text = path.read_text(errors="replace")
            output_text_by_name[path.name] = text
        parsed_outputs[path.name] = _parse_float_values_text(text)

    return parsed_outputs


def _parse_float_values_text(text: str) -> PotentialSampleSet:
    """Parse a whitespace-delimited `x y z value` output payload."""
    coordinates: list[list[float]] = []
    potentials: list[float] = []

    for line in text.splitlines():
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
