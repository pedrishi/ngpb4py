from pathlib import Path

import pytest

from ngpb4py import NgpbConfig, NgpbRunner
from ngpb4py import runner as runner_module
from ngpb4py.backends.base import ExecutionResult
from ngpb4py.inputs import NgpbInputs


class RecordingBackend:
    name = "recording"

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.workdirs: list[Path] = []
        self.inputs: list[NgpbInputs] = []

    def run(self, inputs: NgpbInputs, workdir: Path, nproc: int, ngpb_binary: str) -> ExecutionResult:
        self.workdirs.append(workdir)
        self.inputs.append(inputs)

        stdout_path = workdir / "ngpb.stdout.log"
        stderr_path = workdir / "ngpb.stderr.log"
        stdout_path.write_text("========== [ Building Grid ] ==========\n")
        stderr_path.write_text("")
        (workdir / "phi_surf.txt").write_text("0.0 1.0 2.0 3.0\n")

        if self.fail:
            raise RuntimeError("backend failure")

        return ExecutionResult(
            command=[ngpb_binary, "--prmfile", str(inputs.prmfile)],
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            output_paths=[stdout_path, stderr_path, workdir / "phi_surf.txt"],
        )


def test_runner_uses_unique_per_run_workdirs_and_cleans_on_success(tmp_path):
    backend = RecordingBackend()
    runner = NgpbRunner(backend=backend)
    config = NgpbConfig.defaults()

    result1 = runner.run(config=config, pqr=None, workdir=str(tmp_path), collect_version=False)
    result2 = runner.run(config=config, pqr=None, workdir=str(tmp_path), collect_version=False)

    assert result1.run_id != result2.run_id
    assert backend.workdirs[0] != backend.workdirs[1]
    assert backend.workdirs[0].parent == tmp_path
    assert backend.workdirs[1].parent == tmp_path
    assert not backend.workdirs[0].exists()
    assert not backend.workdirs[1].exists()
    assert list(tmp_path.iterdir()) == []
    assert result1.kept_files is False
    assert result1.provenance["run_id"] == result1.run_id


def test_runner_keeps_workdir_on_error(tmp_path):
    backend = RecordingBackend(fail=True)
    runner = NgpbRunner(backend=backend)

    with pytest.raises(RuntimeError, match="backend failure"):
        runner.run(
            config=NgpbConfig.defaults(),
            pqr=None,
            workdir=str(tmp_path),
            collect_version=False,
        )

    kept_dirs = list(tmp_path.iterdir())
    assert len(kept_dirs) == 1
    assert kept_dirs[0] == backend.workdirs[0]
    assert (kept_dirs[0] / "ngpb.stdout.log").exists()


def test_runner_keeps_workdir_when_keep_files_is_true(tmp_path):
    backend = RecordingBackend()
    runner = NgpbRunner(backend=backend)

    result = runner.run(
        config=NgpbConfig.defaults(),
        pqr=None,
        workdir=str(tmp_path),
        collect_version=False,
        keep_files=True,
    )

    assert result.kept_files is True
    assert result.workdir.exists()
    assert result.workdir.parent == tmp_path
    assert (result.workdir / "phi_surf.txt").exists()


def test_runner_stages_inputs_into_run_workdir(tmp_path):
    source_dir = tmp_path / "source"
    scratch_dir = tmp_path / "scratch"
    source_dir.mkdir()
    scratch_dir.mkdir()

    prm_path = source_dir / "options.prm"
    pqr_path = source_dir / "molecule.pqr"
    aux_path = source_dir / "radius.siz"
    prm_path.write_text("filename = molecule.pqr\nradius_file = radius.siz\n")
    pqr_path.write_text("ATOM\n")
    aux_path.write_text("1.0\n")

    backend = RecordingBackend()
    runner = NgpbRunner(backend=backend)
    inputs = NgpbInputs(prmfile=prm_path, pqrfile=pqr_path, aux_files=[aux_path])

    result = runner.run(
        config=NgpbConfig.defaults(),
        pqr=None,
        workdir=str(scratch_dir),
        inputs=inputs,
        collect_version=False,
        keep_files=True,
    )

    staged_inputs = backend.inputs[0]
    assert staged_inputs.prmfile.parent == result.workdir
    assert staged_inputs.pqrfile == result.workdir / pqr_path.name
    assert staged_inputs.aux_files == [result.workdir / aux_path.name]
    assert staged_inputs.prmfile.read_text() == prm_path.read_text()


def test_runner_verbose_override_updates_existing_handler_level(monkeypatch):
    runner_module._LOGGER.handlers.clear()

    runner = NgpbRunner(backend=RecordingBackend(), verbosity=0)
    runner.run(
        config=NgpbConfig.defaults(),
        pqr=None,
        workdir="/tmp",
        collect_version=False,
    )
    assert runner_module._LOGGER.handlers[0].level == runner_module.logging.WARNING

    runner.run(
        config=NgpbConfig.defaults(),
        pqr=None,
        workdir="/tmp",
        collect_version=False,
        verbose=3,
    )
    assert runner_module._LOGGER.handlers[0].level == runner_module.logging.DEBUG
