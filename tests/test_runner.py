from pathlib import Path

import pytest

from ngpb4py import NgpbConfig, NgpbRunner
from ngpb4py.container import ContainerBackend, ExecutionResult


def make_empty_config() -> NgpbConfig:
    return NgpbConfig()


def install_fake_container_run(monkeypatch, *, fail: bool = False):
    workdirs: list[Path] = []
    captured_prm_files: list[Path] = []

    def fake_run(
        self,
        prm_f: str | Path,
        workdir: Path,
        nproc: int,
        ngpb_binary: str,
        collect_version: bool = True,
    ) -> ExecutionResult:
        del self, nproc, collect_version
        workdirs.append(workdir)
        captured_prm_files.append(Path(prm_f))

        stdout_path = workdir / "ngpb.stdout.log"
        stderr_path = workdir / "ngpb.stderr.log"
        stdout_path.write_text("========== [ Building Grid ] ==========\n")
        stderr_path.write_text("")
        (workdir / "phi_surf.txt").write_text("0.0 1.0 2.0 3.0\n")

        if fail:
            raise RuntimeError("backend failure")

        return ExecutionResult(
            command=[ngpb_binary, "--prmfile", str(prm_f)],
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            output_paths=[stdout_path, stderr_path, workdir / "phi_surf.txt"],
        )

    monkeypatch.setattr(ContainerBackend, "run", fake_run)
    return workdirs, captured_prm_files


def test_runner_uses_unique_per_run_workdirs_and_cleans_on_success(tmp_path, monkeypatch):
    workdirs, _ = install_fake_container_run(monkeypatch)
    runner = NgpbRunner()
    config = make_empty_config()

    result1 = runner.run(config=config, workdir=str(tmp_path), collect_version=False)
    result2 = runner.run(config=config, workdir=str(tmp_path), collect_version=False)

    assert result1.run_id != result2.run_id
    assert workdirs[0] != workdirs[1]
    assert workdirs[0].parent == tmp_path
    assert workdirs[1].parent == tmp_path
    assert not workdirs[0].exists()
    assert not workdirs[1].exists()
    assert list(tmp_path.iterdir()) == []
    assert result1.kept_files is False
    assert result1.provenance["run_id"] == result1.run_id


def test_runner_keeps_workdir_on_error(tmp_path, monkeypatch):
    workdirs, _ = install_fake_container_run(monkeypatch, fail=True)
    runner = NgpbRunner()

    with pytest.raises(RuntimeError, match="backend failure"):
        runner.run(config=make_empty_config(), workdir=str(tmp_path), collect_version=False)

    kept_dirs = list(tmp_path.iterdir())
    assert len(kept_dirs) == 1
    assert kept_dirs[0] == workdirs[0]
    assert (kept_dirs[0] / "ngpb.stdout.log").exists()


def test_runner_keeps_workdir_when_keep_files_is_true(tmp_path, monkeypatch):
    install_fake_container_run(monkeypatch)
    runner = NgpbRunner()

    result = runner.run(
        config=make_empty_config(), workdir=str(tmp_path), collect_version=False, keep_files=True
    )

    assert result.kept_files is True
    assert result.workdir.exists()
    assert result.workdir.parent == tmp_path
    assert (result.workdir / "phi_surf.txt").exists()


def test_runner_stages_prm_referenced_inputs_into_run_workdir(tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    scratch_dir = tmp_path / "scratch"
    source_dir.mkdir()
    scratch_dir.mkdir()

    prm_path = source_dir / "options.prm"
    pqr_path = source_dir / "molecule.pqr"
    aux_path = source_dir / "radius.siz"
    prm_path.write_text("filetype = pqr\nfilename = molecule.pqr\nradius_file = radius.siz\n")
    pqr_path.write_text("ATOM\n")
    aux_path.write_text("1.0\n")

    _, captured_prm_files = install_fake_container_run(monkeypatch)
    runner = NgpbRunner()
    config = NgpbConfig.from_prm(str(prm_path))

    result = runner.run(
        config=config, workdir=str(scratch_dir), collect_version=False, keep_files=True
    )

    prmfile_path = captured_prm_files[0]
    assert prmfile_path.parent == result.workdir
    assert (result.workdir / pqr_path.name).exists()
    assert (result.workdir / aux_path.name).exists()
    assert "filename = molecule.pqr" in prmfile_path.read_text()
    assert "radius_file = radius.siz" in prmfile_path.read_text()


def test_runner_raises_when_prm_referenced_input_is_missing(tmp_path):
    source_dir = tmp_path / "source"
    scratch_dir = tmp_path / "scratch"
    source_dir.mkdir()
    scratch_dir.mkdir()

    prm_path = source_dir / "options.prm"
    prm_path.write_text("filename = missing.pqr\n")

    config = NgpbConfig.from_prm(str(prm_path))
    runner = NgpbRunner()

    with pytest.raises(FileNotFoundError, match="filename"):
        runner.run(config=config, workdir=str(scratch_dir), collect_version=False)


def test_runner_ignores_output_only_prm_paths(tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    scratch_dir = tmp_path / "scratch"
    source_dir.mkdir()
    scratch_dir.mkdir()

    prm_path = source_dir / "options.prm"
    pdb_path = source_dir / "molecule.pdb"
    prm_path.write_text("filetype = pdb\nfilename = molecule.pdb\nname_pqr = missing_output.pqr\n")
    pdb_path.write_text("ATOM\n")

    _, captured_prm_files = install_fake_container_run(monkeypatch)
    runner = NgpbRunner()
    config = NgpbConfig.from_prm(str(prm_path))

    runner.run(config=config, workdir=str(scratch_dir), collect_version=False, keep_files=True)

    prmfile_path = captured_prm_files[0]
    assert prmfile_path.parent.exists()
    assert "name_pqr = missing_output.pqr" in prmfile_path.read_text()
    assert not (prmfile_path.parent / "missing_output.pqr").exists()


def test_runner_verbose_override_updates_existing_handler_level(monkeypatch):
    from ngpb4py import verbose

    verbose._LOGGER.handlers.clear()
    install_fake_container_run(monkeypatch)

    runner = NgpbRunner(verbosity=0)
    runner.run(config=make_empty_config(), workdir="/tmp", collect_version=False)
    assert verbose._LOGGER.handlers[0].level == verbose.logging.WARNING

    runner.run(config=make_empty_config(), workdir="/tmp", collect_version=False, verbose=3)
    assert verbose._LOGGER.handlers[0].level == verbose.logging.DEBUG


def test_runner_passes_custom_apptainer_path_to_container_backend():
    custom_path = "/opt/apptainer/bin/apptainer"
    runner = NgpbRunner(apptainer_path=custom_path)

    backend = ContainerBackend(
        image=runner.container_image,
        runtime=runner.container_runtime,
        apptainer_path=runner.apptainer_path,
        extra_args=runner.container_extra_args,
        exec_args=runner.container_exec_args,
    )

    assert isinstance(backend, ContainerBackend)
    assert backend.apptainer_path == custom_path


def test_runner_passes_custom_runtime_and_image_to_container_backend():
    runner = NgpbRunner(
        container_runtime="docker", container_image="ghcr.io/example/nextgenpb:latest"
    )

    backend = ContainerBackend(
        image=runner.container_image,
        runtime=runner.container_runtime,
        apptainer_path=runner.apptainer_path,
        extra_args=runner.container_extra_args,
        exec_args=runner.container_exec_args,
    )

    assert backend.runtime == "docker"
    assert backend.image == "ghcr.io/example/nextgenpb:latest"


def test_runner_passes_custom_sif_to_container_backend():
    sif_path = "/tmp/custom-nextgenpb.sif"
    runner = NgpbRunner(container_runtime="apptainer", container_image=sif_path)

    backend = ContainerBackend(
        image=runner.container_image,
        runtime=runner.container_runtime,
        apptainer_path=runner.apptainer_path,
        extra_args=runner.container_extra_args,
        exec_args=runner.container_exec_args,
    )

    assert backend.runtime == "apptainer"
    assert backend.image == sif_path
