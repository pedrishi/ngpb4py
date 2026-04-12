"""Container-backed execution backend for NextGenPB."""

from __future__ import annotations

import logging
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from .helpers.run_container import detect_runtime, execute_command, prepare_container_image

_LOGGER = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Low-level execution artefacts returned by a backend run."""

    command: list[str]
    stdout_path: Path
    stderr_path: Path
    output_paths: list[Path] | None = None
    provenance: dict[str, str] = field(default_factory=dict)


@dataclass
class ContainerBackend:
    """Execute NextGenPB inside an Apptainer-compatible container image."""

    name: str = "container"
    image: str = (
        "https://github.com/concept-lab/NextGenPB/releases/download/NextGenPB_v1.0.0/NextGenPB.sif"
    )
    apptainer_path: str | None = None
    extra_args: list[str] | None = None
    exec_args: list[str] | None = None
    stream_output: bool = False
    _runtime_cmd: str | None = field(default=None, init=False, repr=False)
    _resolved_image: str | None = field(default=None, init=False, repr=False)
    _instance_name: str | None = field(default=None, init=False, repr=False)
    _instance_scratch_dir: Path | None = field(default=None, init=False, repr=False)
    _version_binary: str | None = field(default=None, init=False, repr=False)
    _cached_ngpb_version: str | None = field(default=None, init=False, repr=False)
    _version_detected: bool = field(default=False, init=False, repr=False)

    def run(
        self, prm_f: Path, workdir: Path, nproc: int, ngpb_binary: str, collect_version: bool = True
    ) -> ExecutionResult:
        """Run the configured container backend and collect execution artefacts."""
        runtime_cmd = self._get_runtime_cmd()
        resolved_image = self._get_resolved_image()
        self._ensure_instance(runtime_cmd, resolved_image, workdir.parent)
        command = self._build_exec_command(
            workdir=workdir, prm_f=prm_f, nproc=nproc, ngpb_binary=ngpb_binary
        )

        _LOGGER.debug("Execution command: %s\n", " ".join(command))

        stdout_path = workdir / "ngpb.stdout.log"
        stderr_path = workdir / "ngpb.stderr.log"
        execute_command(
            command=command,
            workdir=workdir,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stream_output=self.stream_output,
        )

        candidates = [
            workdir / "phi_surf.txt",
            workdir / "phi_nodes.txt",
            workdir / "phi_on_atoms.txt",
        ]
        existing_outputs = [path for path in candidates if path.exists()]
        return ExecutionResult(
            command=command,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            output_paths=existing_outputs,
            provenance=_collect_provenance(
                command=command,
                nproc=nproc,
                backend_name=self.name,
                ngpb_version=self._get_ngpb_version(ngpb_binary, collect_version=collect_version),
                collect_version=collect_version,
            ),
        )

    def close(self) -> None:
        """Stop any persistent Apptainer instance held by the backend."""
        if self._instance_name is None:
            return
        runtime_cmd = self._get_runtime_cmd()
        command = [runtime_cmd, "instance", "stop", self._instance_name]
        _run_control_command(command)
        self._instance_name = None
        self._instance_scratch_dir = None

    def _get_runtime_cmd(self) -> str:
        if self._runtime_cmd is None:
            self._runtime_cmd = detect_runtime(self.apptainer_path)
        return self._runtime_cmd

    def _get_resolved_image(self) -> str:
        if self._resolved_image is None:
            self._resolved_image = prepare_container_image("apptainer", self.image)
        return self._resolved_image

    def _ensure_instance(self, runtime_cmd: str, resolved_image: str, scratch_dir: Path) -> None:
        scratch_dir = scratch_dir.resolve()
        if self._instance_name is not None and self._instance_scratch_dir == scratch_dir:
            return

        self.close()
        instance_name = f"ngpb4py-{uuid.uuid4().hex}"
        command = [
            runtime_cmd,
            *(self.extra_args or []),
            "instance",
            "start",
            *(self.exec_args or []),
            "--bind",
            f"{scratch_dir}:/App",
            resolved_image,
            instance_name,
        ]
        _run_control_command(command, cwd=scratch_dir)
        self._instance_name = instance_name
        self._instance_scratch_dir = scratch_dir

    def _build_exec_command(
        self, workdir: Path, prm_f: Path, nproc: int, ngpb_binary: str
    ) -> list[str]:
        runtime_cmd = self._get_runtime_cmd()
        if self._instance_name is None:
            raise RuntimeError("Persistent Apptainer instance was not initialized")

        container_workdir = PurePosixPath("/App") / workdir.name
        command = [
            runtime_cmd,
            *(self.extra_args or []),
            "exec",
            *(self.exec_args or []),
            "--pwd",
            str(container_workdir),
            f"instance://{self._instance_name}",
            *_build_solver_command(nproc=nproc, ngpb_binary=ngpb_binary, prm_filename=prm_f.name),
        ]
        return command

    def _get_ngpb_version(self, ngpb_binary: str, *, collect_version: bool) -> str | None:
        if not collect_version:
            return None
        if self._version_detected and self._version_binary == ngpb_binary:
            return self._cached_ngpb_version

        self._cached_ngpb_version = _detect_ngpb_version(ngpb_binary)
        self._version_binary = ngpb_binary
        self._version_detected = True
        return self._cached_ngpb_version


def _collect_provenance(
    command: list[str],
    nproc: int,
    backend_name: str,
    ngpb_version: str | None,
    collect_version: bool = True,
) -> dict[str, str]:
    """Collect reproducibility metadata for a backend execution."""
    provenance = {"backend": backend_name, "nproc": str(nproc), "command": " ".join(command)}
    if collect_version and ngpb_version:
        provenance["ngpb_version"] = ngpb_version
    return provenance


def _build_solver_command(nproc: int, ngpb_binary: str, prm_filename: str) -> list[str]:
    command = [ngpb_binary, "--prmfile", prm_filename]
    if nproc == 1:
        return command
    return ["mpirun", "-np", str(nproc), *command]


def _run_control_command(command: list[str], cwd: Path | None = None) -> None:
    completed = subprocess.run(  # noqa: S603
        command, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
    )
    if completed.returncode != 0:
        raise subprocess.CalledProcessError(completed.returncode, command)


def _detect_ngpb_version(ngpb_binary: str) -> str | None:
    """Best-effort detection of the local NextGenPB binary version."""
    try:
        output = subprocess.check_output([ngpb_binary, "--version"], stderr=subprocess.STDOUT)
        return output.decode(errors="replace").strip().splitlines()[0]
    except Exception:
        return None
