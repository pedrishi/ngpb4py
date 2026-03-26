from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .helpers.run_container import (
    container_digest,
    detect_runtime,
    execute_command,
    prepare_container_image,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    command: list[str]
    stdout_path: Path
    stderr_path: Path
    output_paths: list[Path] | None = None
    container_digest: str | None = None
    provenance: dict[str, str] = field(default_factory=dict)


@dataclass
class ContainerBackend:
    name: str = "container"
    image: str = (
        "https://github.com/concept-lab/NextGenPB/releases/download/NextGenPB_v1.0.0/NextGenPB.sif"
    )
    apptainer_path: str | None = None
    extra_args: list[str] | None = None
    exec_args: list[str] | None = None
    stream_output: bool = False

    def run(
        self, prm_f: Path, workdir: Path, nproc: int, ngpb_binary: str, collect_version: bool = True
    ) -> ExecutionResult:
        runtime_cmd = detect_runtime(self.apptainer_path)
        resolved_image = prepare_container_image("apptainer", self.image)

        mount_arg = f"{workdir}:/App"
        base_cmd = [
            runtime_cmd,
            "exec",
            *(self.exec_args or []),
            "--pwd",
            "/App",
            "--bind",
            mount_arg,
            resolved_image,
            "mpirun",
            "-np",
            str(nproc),
        ]

        command = base_cmd + [ngpb_binary, "--prmfile", str(prm_f)]
        if self.extra_args:
            command[1:1] = self.extra_args

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

        digest = container_digest(resolved_image)
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
            container_digest=digest,
            provenance=_collect_provenance(
                command=command,
                nproc=nproc,
                backend_name=self.name,
                container_digest=digest,
                ngpb_binary=ngpb_binary,
                collect_version=collect_version,
            ),
        )


def _collect_provenance(
    command: list[str],
    nproc: int,
    backend_name: str,
    container_digest: str | None,
    ngpb_binary: str,
    collect_version: bool = True,
) -> dict[str, str]:
    provenance = {"backend": backend_name, "nproc": str(nproc), "command": " ".join(command)}
    if container_digest:
        provenance["container_digest"] = container_digest
    if collect_version:
        version = _detect_ngpb_version(ngpb_binary)
        if version:
            provenance["ngpb_version"] = version
    return provenance


def _detect_ngpb_version(ngpb_binary: str) -> str | None:
    try:
        output = subprocess.check_output([ngpb_binary, "--version"], stderr=subprocess.STDOUT)
        return output.decode(errors="replace").strip().splitlines()[0]
    except Exception:
        return None
