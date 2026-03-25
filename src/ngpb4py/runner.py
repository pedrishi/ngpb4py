from __future__ import annotations

import logging
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from .config import NgpbConfig, packaged_default_input
from .container import ContainerBackend
from .result import NgpbResult
from .verbose import _configure_logging

_LOGGER = logging.getLogger(__name__)


@dataclass
class NgpbRunner:
    nproc: int = 1
    ngpb_binary: str = "ngpb"
    container_image: str = (
        "https://github.com/concept-lab/NextGenPB/releases/download/NextGenPB_v1.0.0/NextGenPB.sif"
    )
    container_runtime: str | None = "apptainer"
    apptainer_path: str | None = None
    container_extra_args: list[str] | None = None
    container_exec_args: list[str] | None = None
    verbosity: int = 1

    def run(
        self,
        config: NgpbConfig,
        workdir: str,
        collect_version: bool = True,
        verbose: int | None = None,
        keep_files: bool = False,
    ) -> NgpbResult:
        effective_verbose = self.verbosity if verbose is None else verbose
        _configure_logging(effective_verbose)

        _LOGGER.info("Starting NextGenPB run")
        scratch_dir = Path(workdir)
        scratch_dir.mkdir(parents=True, exist_ok=True)
        run_id, run_workdir = _create_run_workdir(scratch_dir)
        _LOGGER.debug("Using scratch_dir=%s run_id=%s workdir=%s", scratch_dir, run_id, run_workdir)

        _LOGGER.info("Staging run inputs into %s", run_workdir)
        prm_path, staged_paths = _stage_inputs(config=config, workdir=run_workdir)

        if config.data.get("filetype") == "pqr" and "filename" not in staged_paths:
            _LOGGER.warning("No PQR file provided; proceeding without --pqrfile")

        input_paths = [str(prm_path), *(str(path) for path in staged_paths.values())]
        _LOGGER.debug("Input paths: %s", ", ".join(input_paths))

        _LOGGER.debug(
            "Creating container backend with image=%s runtime=%s",
            self.container_image,
            self.container_runtime,
        )
        backend = ContainerBackend(
            image=self.container_image,
            runtime=self.container_runtime,
            apptainer_path=self.apptainer_path,
            extra_args=self.container_extra_args,
            exec_args=self.container_exec_args,
        )

        backend.stream_output = effective_verbose >= 3
        _LOGGER.info("Running backend %s with %d process(es)", backend.name, self.nproc)
        cleanup_workdir = not keep_files
        try:
            exec_result = backend.run(
                prm_f=prm_path,
                workdir=run_workdir,
                nproc=self.nproc,
                ngpb_binary=self.ngpb_binary,
                collect_version=collect_version,
            )
            _LOGGER.info("Backend execution completed")

            provenance = dict(exec_result.provenance)
            if not provenance:
                provenance = {
                    "backend": backend.name,
                    "nproc": str(self.nproc),
                    "command": " ".join(exec_result.command),
                }
                if exec_result.container_digest:
                    provenance["container_digest"] = exec_result.container_digest
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


def _stage_inputs(config: NgpbConfig, workdir: Path) -> tuple[Path, dict[str, Path]]:
    staged_data = dict(config.data)
    staged_paths: dict[str, Path] = {}

    for key in config.iter_input_file_keys():
        if config.uses_packaged_default_input(key):
            resource = packaged_default_input(key)
            staged_path = _copy_packaged_input_file(resource, workdir)
        else:
            source_path = config.resolve_input_file(key)
            if not source_path.exists():
                raise FileNotFoundError(
                    f"Input file referenced by '{key}' does not exist: {source_path}"
                )
            staged_path = _copy_input_file(source_path, workdir)

        staged_paths[key] = staged_path
        staged_data[key] = staged_path.name

    staged_config = config.with_updates(staged_data)
    prm_path = workdir / config.prm_filename()
    prm_path.write_text(staged_config.to_prm())

    return prm_path, staged_paths


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


def _copy_packaged_input_file(resource, workdir: Path) -> Path:
    destination = workdir / resource.name
    if destination.exists():
        raise ValueError(
            f"Conflicting staged input filename '{resource.name}'. "
            "Rename one of the inputs before running."
        )
    destination.write_bytes(resource.read_bytes())
    return destination
