from __future__ import annotations

import logging
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .backends.base import ExecutionResult, NgpbBackend
from .backends.container import ContainerBackend
from .config import NgpbConfig
from .inputs import NgpbInputs
from .provenance import collect_provenance
from .result import NgpbResult


@dataclass
class NgpbRunner:
    nproc: int = 1
    ngpb_binary: str = "ngpb"
    container_image: str = (
        "https://github.com/concept-lab/NextGenPB/releases/download/"
        "NextGenPB_v1.0.0/NextGenPB.sif"
    )
    container_runtime: Optional[str] = "apptainer"
    container_extra_args: Optional[List[str]] = None
    container_exec_args: Optional[List[str]] = None
    backend: Optional[NgpbBackend] = None
    verbosity: int = 1

    def _make_backend(self) -> NgpbBackend:
        if self.backend is not None:
            _LOGGER.debug("Using preconfigured backend: %s", self.backend)
            return self.backend
        _LOGGER.debug(
            "Creating container backend with image=%s runtime=%s",
            self.container_image,
            self.container_runtime,
        )
        return ContainerBackend(
            image=self.container_image,
            runtime=self.container_runtime,
            extra_args=self.container_extra_args,
            exec_args=self.container_exec_args,
        )

    def run(
        self,
        config: NgpbConfig,
        pqr: Optional[str],
        workdir: str,
        inputs: Optional[NgpbInputs] = None,
        collect_version: bool = True,
        verbose: Optional[int] = None,
        keep_files: bool = False,
    ) -> NgpbResult:
        effective_verbose = self.verbosity if verbose is None else verbose
        _configure_logging(effective_verbose)

        _LOGGER.info("Starting NextGenPB run")
        scratch_dir = Path(workdir)
        scratch_dir.mkdir(parents=True, exist_ok=True)
        run_id, run_workdir = _create_run_workdir(scratch_dir)
        _LOGGER.debug("Using scratch_dir=%s run_id=%s workdir=%s", scratch_dir, run_id, run_workdir)

        if inputs is None:
            _LOGGER.info("Generating run inputs in %s", run_workdir)
        else:
            _LOGGER.info("Staging provided inputs into %s", run_workdir)
        staged_inputs = _stage_inputs(
            config=config,
            pqr=pqr,
            inputs=inputs,
            workdir=run_workdir,
        )

        if staged_inputs.pqrfile is None:
            _LOGGER.warning("No PQR file provided; proceeding without --pqrfile")

        input_paths = [str(path) for path in staged_inputs.iter_paths()]
        _LOGGER.debug("Input paths: %s", ", ".join(input_paths))

        backend = self._make_backend()
        if hasattr(backend, "stream_output"):
            setattr(backend, "stream_output", effective_verbose >= 3)
        _LOGGER.info("Running backend %s with %d process(es)", backend.name, self.nproc)
        cleanup_workdir = not keep_files
        try:
            exec_result: ExecutionResult = backend.run(
                inputs=staged_inputs,
                workdir=run_workdir,
                nproc=self.nproc,
                ngpb_binary=self.ngpb_binary,
            )
            _LOGGER.info("Backend execution completed")

            provenance = collect_provenance(
                command=exec_result.command,
                nproc=self.nproc,
                backend_name=backend.name,
                container_digest=exec_result.container_digest,
                ngpb_binary=self.ngpb_binary,
                collect_version=collect_version,
            )
            provenance["run_id"] = run_id
            _LOGGER.debug("Collected provenance entries: %d", len(provenance))

            output_paths = exec_result.output_paths or []
            result = NgpbResult.from_logs(
                run_id=run_id,
                scratch_dir=scratch_dir,
                workdir=run_workdir,
                kept_files=keep_files,
                command=exec_result.command,
                stdout_path=exec_result.stdout_path,
                stderr_path=exec_result.stderr_path,
                output_paths=output_paths,
                provenance=provenance,
            )
            _LOGGER.info("Parsed %d documented log section(s)", result.log.section_count())
            if output_paths:
                _LOGGER.info("Collected %d output file(s)", len(output_paths))
            _LOGGER.info("NextGenPB run finished")
            return result
        except Exception:
            cleanup_workdir = False
            _LOGGER.exception("NextGenPB run failed; keeping workdir %s", run_workdir)
            raise
        finally:
            if cleanup_workdir:
                shutil.rmtree(run_workdir)
                _LOGGER.debug("Removed workdir for run_id=%s", run_id)


def _create_run_workdir(scratch_dir: Path) -> tuple[str, Path]:
    while True:
        run_id = uuid.uuid4().hex
        run_workdir = scratch_dir / run_id
        try:
            run_workdir.mkdir()
            return run_id, run_workdir
        except FileExistsError:
            continue


def _stage_inputs(
    config: NgpbConfig,
    pqr: Optional[str],
    inputs: Optional[NgpbInputs],
    workdir: Path,
) -> NgpbInputs:
    if inputs is None:
        prm_path = workdir / "ngpb.prm"
        prm_path.write_text(config.to_prm())
        pqr_path = _copy_input_file(Path(pqr), workdir) if pqr else None
        return NgpbInputs(prmfile=prm_path, pqrfile=pqr_path)

    copied_paths = {
        source: _copy_input_file(source, workdir)
        for source in inputs.iter_paths()
    }
    return NgpbInputs(
        prmfile=copied_paths[inputs.prmfile],
        pqrfile=copied_paths[inputs.pqrfile] if inputs.pqrfile else None,
        aux_files=[copied_paths[path] for path in inputs.aux_files],
    )


def _copy_input_file(path: Path, workdir: Path) -> Path:
    destination = workdir / path.name
    if destination.exists():
        source_resolved = path.resolve()
        destination_resolved = destination.resolve()
        if source_resolved == destination_resolved:
            return destination
        raise ValueError(
            f"Conflicting staged input filename '{path.name}'. "
            "Rename one of the inputs before running."
        )
    shutil.copy2(path, destination)
    return destination


_LOGGER = logging.getLogger("ngpb4py")


_VERBOSITY_LEVELS = {
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
    3: logging.DEBUG,
}


def _configure_logging(verbosity: int) -> None:
    level = _VERBOSITY_LEVELS.get(verbosity, logging.DEBUG)
    _LOGGER.setLevel(level)

    if not _LOGGER.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        _LOGGER.addHandler(handler)
        _LOGGER.propagate = False

    for handler in _LOGGER.handlers:
        handler.setLevel(level)
