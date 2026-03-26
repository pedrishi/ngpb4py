import io
import subprocess
import threading
import time

import pytest

from ngpb4py.container import ContainerBackend
from ngpb4py.helpers.run_container import detect_runtime


def test_detect_runtime_uses_apptainer_from_path(monkeypatch):
    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/bin/apptainer" if name == "apptainer" else None
    )

    assert detect_runtime() == "/usr/bin/apptainer"


def test_detect_runtime_uses_custom_absolute_apptainer_path(tmp_path, monkeypatch):
    custom_apptainer = tmp_path / "bin" / "apptainer"
    custom_apptainer.parent.mkdir()
    custom_apptainer.write_text("#!/bin/sh\n")
    custom_apptainer.chmod(custom_apptainer.stat().st_mode | 0o111)
    monkeypatch.setattr("shutil.which", lambda name: None)

    assert detect_runtime(str(custom_apptainer)) == str(custom_apptainer)


def test_detect_runtime_rejects_non_absolute_apptainer_path():
    with pytest.raises(RuntimeError, match="absolute path"):
        detect_runtime("apptainer")


def test_detect_runtime_raises_when_apptainer_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)

    with pytest.raises(RuntimeError, match="Apptainer runtime was not found in PATH"):
        detect_runtime()


def test_container_command_building(tmp_path, monkeypatch):
    prmfile = tmp_path / "ngpb.prm"
    prmfile.write_text("solver.max_iterations = 1\n")

    captured = {}

    def fake_run(command, cwd, stdout, stderr, check):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0)

    def fake_check_output(command, stderr=None):
        del stderr
        return b"sha256:dummy local-image"

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("subprocess.check_output", fake_check_output)
    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/bin/apptainer" if name == "apptainer" else None
    )

    backend = ContainerBackend(image="/tmp/NextGenPB.sif")
    backend.run(prm_f=prmfile, workdir=tmp_path, nproc=1, ngpb_binary="ngpb")

    assert captured["command"][0:11] == [
        "/usr/bin/apptainer",
        "exec",
        "--pwd",
        "/App",
        "--bind",
        f"{tmp_path}:/App",
        "/tmp/NextGenPB.sif",
        "mpirun",
        "-np",
        "1",
        "ngpb",
    ]
    assert captured["command"][-2:] == ["--prmfile", str(prmfile)]


def test_apptainer_remote_image_download_with_progress(tmp_path, monkeypatch):
    from ngpb4py.helpers import download_image

    prmfile = tmp_path / "ngpb.prm"
    prmfile.write_text("solver.max_iterations = 1\n")

    class FakeResponse:
        def __init__(self):
            self.headers = {"Content-Length": "10"}
            self._chunks = [b"12345", b"67890"]

        def read(self, size):
            if not self._chunks:
                return b""
            return self._chunks.pop(0)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeStderr(io.StringIO):
        def isatty(self):
            return True

    captured = {}
    fake_stderr = FakeStderr()

    def fake_urlopen(url):
        captured["url"] = url
        return FakeResponse()

    def fake_run(command, cwd, stdout, stderr, check):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setenv("NGPB_CONTAINER_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(download_image, "urlopen", fake_urlopen)
    monkeypatch.setattr(download_image.sys, "stderr", fake_stderr)
    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr(
        "subprocess.check_output", lambda command, stderr=None: b"sha256:dummy local-image"
    )
    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/bin/apptainer" if name == "apptainer" else None
    )

    backend = ContainerBackend(image="https://example.org/NextGenPB.sif")
    backend.run(prm_f=prmfile, workdir=tmp_path, nproc=1, ngpb_binary="ngpb")

    local_image = tmp_path / "cache" / "NextGenPB.sif"
    assert captured["url"] == "https://example.org/NextGenPB.sif"
    assert str(local_image) in captured["command"]
    assert local_image.exists()
    assert "Downloading container image" in fake_stderr.getvalue()
    assert "100%" in fake_stderr.getvalue()


def test_apptainer_exec_args_are_inserted_after_exec(tmp_path, monkeypatch):
    prmfile = tmp_path / "ngpb.prm"
    prmfile.write_text("solver.max_iterations = 1\n")

    captured = {}

    def fake_run(command, cwd, stdout, stderr, check):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr(
        "subprocess.check_output", lambda command, stderr=None: b"sha256:dummy local-image"
    )
    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/bin/apptainer" if name == "apptainer" else None
    )

    backend = ContainerBackend(image="/tmp/NextGenPB.sif", exec_args=["--nv", "--containall"])
    backend.run(prm_f=prmfile, workdir=tmp_path, nproc=2, ngpb_binary="ngpb")

    assert captured["command"][0].endswith("apptainer")
    assert captured["command"][1:12] == [
        "exec",
        "--nv",
        "--containall",
        "--pwd",
        "/App",
        "--bind",
        f"{tmp_path}:/App",
        "/tmp/NextGenPB.sif",
        "mpirun",
        "-np",
        "2",
    ]


def test_apptainer_uses_custom_absolute_path_when_not_on_path(tmp_path, monkeypatch):
    prmfile = tmp_path / "ngpb.prm"
    prmfile.write_text("solver.max_iterations = 1\n")

    custom_apptainer = tmp_path / "bin" / "apptainer"
    custom_apptainer.parent.mkdir()
    custom_apptainer.write_text("#!/bin/sh\n")
    custom_apptainer.chmod(custom_apptainer.stat().st_mode | 0o111)

    captured = {}

    def fake_run(command, cwd, stdout, stderr, check):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("shutil.which", lambda name: None)

    backend = ContainerBackend(apptainer_path=str(custom_apptainer), image="/tmp/NextGenPB.sif")
    backend.run(prm_f=prmfile, workdir=tmp_path, nproc=1, ngpb_binary="ngpb")

    assert captured["command"][0] == str(custom_apptainer)
    assert captured["command"][1] == "exec"


def test_container_run_raises_on_nonzero_exit(tmp_path, monkeypatch):
    prmfile = tmp_path / "ngpb.prm"
    prmfile.write_text("solver.max_iterations = 1\n")

    def fake_run(command, cwd, stdout, stderr, check):
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/bin/apptainer" if name == "apptainer" else None
    )

    backend = ContainerBackend(image="/tmp/NextGenPB.sif")
    with pytest.raises(subprocess.CalledProcessError, match="returned non-zero exit status 7"):
        backend.run(prm_f=prmfile, workdir=tmp_path, nproc=1, ngpb_binary="ngpb")


def test_streaming_container_run_raises_on_nonzero_exit(tmp_path, monkeypatch):
    prmfile = tmp_path / "ngpb.prm"
    prmfile.write_text("solver.max_iterations = 1\n")

    class FakeProcess:
        def __init__(self):
            self.stdout = io.StringIO("stdout\n")
            self.stderr = io.StringIO("stderr\n")

        def wait(self):
            return 9

    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: FakeProcess())
    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/bin/apptainer" if name == "apptainer" else None
    )

    backend = ContainerBackend(image="/tmp/NextGenPB.sif", stream_output=True)
    with pytest.raises(subprocess.CalledProcessError, match="returned non-zero exit status 9"):
        backend.run(prm_f=prmfile, workdir=tmp_path, nproc=1, ngpb_binary="ngpb")


def test_apptainer_remote_image_download_is_locked(tmp_path, monkeypatch):
    from ngpb4py import container as container_backend
    from ngpb4py.helpers import download_image

    destination = tmp_path / "cache" / "NextGenPB.sif"
    destination.parent.mkdir()
    monkeypatch.setenv("NGPB_CONTAINER_CACHE_DIR", str(destination.parent))
    started = threading.Event()
    release = threading.Event()
    call_count = 0

    def fake_download(url, dest):
        nonlocal call_count
        call_count += 1
        started.set()
        release.wait(timeout=2)
        dest.write_text("image")

    monkeypatch.setattr(download_image, "download_with_progress", fake_download)

    thread_one = threading.Thread(
        target=container_backend.prepare_container_image,
        args=("apptainer", "https://example.org/NextGenPB.sif"),
    )
    thread_two = threading.Thread(
        target=container_backend.prepare_container_image,
        args=("apptainer", "https://example.org/NextGenPB.sif"),
    )

    thread_one.start()
    started.wait(timeout=2)
    thread_two.start()
    time.sleep(0.1)
    release.set()
    thread_one.join(timeout=2)
    thread_two.join(timeout=2)

    assert call_count == 1
