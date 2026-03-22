import io
import subprocess
import threading
import time

from ngpb4py.container import ContainerBackend


def test_container_command_building(tmp_path, monkeypatch):
    prmfile = tmp_path / "ngpb.prm"
    prmfile.write_text("solver.max_iterations = 1\n")

    captured = {}

    def fake_run(command, cwd, stdout, stderr, check):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0)

    def fake_check_output(command):
        return b"sha256:dummy"

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("subprocess.check_output", fake_check_output)
    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/bin/docker" if name == "docker" else None
    )

    backend = ContainerBackend(runtime="docker", image="conceptlab/nextgenpb:latest")
    backend.run(prm_f=prmfile, workdir=tmp_path, nproc=1, ngpb_binary="ngpb")

    assert captured["command"][0:13] == [
        "docker",
        "run",
        "--rm",
        "--cpus",
        "1",
        "--env",
        "NGPB_NPROC=1",
        "-v",
        f"{tmp_path}:/App",
        "-w",
        "/App",
        "conceptlab/nextgenpb:latest",
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

    backend = ContainerBackend(runtime="apptainer", image="https://example.org/NextGenPB.sif")
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

    backend = ContainerBackend(
        runtime="apptainer", image="/tmp/NextGenPB.sif", exec_args=["--nv", "--containall"]
    )
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

    def fake_which(name):
        return None

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("shutil.which", fake_which)

    backend = ContainerBackend(
        runtime=None, apptainer_path=str(custom_apptainer), image="/tmp/NextGenPB.sif"
    )
    backend.run(prm_f=prmfile, workdir=tmp_path, nproc=1, ngpb_binary="ngpb")

    assert captured["command"][0] == str(custom_apptainer)
    assert captured["command"][1] == "exec"


def test_apptainer_custom_path_must_be_absolute(tmp_path):
    prmfile = tmp_path / "ngpb.prm"
    prmfile.write_text("solver.max_iterations = 1\n")
    backend = ContainerBackend(
        runtime="apptainer", apptainer_path="apptainer", image="/tmp/NextGenPB.sif"
    )

    try:
        backend.run(prm_f=prmfile, workdir=tmp_path, nproc=1, ngpb_binary="ngpb")
    except RuntimeError as exc:
        assert "absolute path" in str(exc)
    else:
        raise AssertionError("ContainerBackend should reject non-absolute Apptainer paths")


def test_container_run_raises_on_nonzero_exit(tmp_path, monkeypatch):
    prmfile = tmp_path / "ngpb.prm"
    prmfile.write_text("solver.max_iterations = 1\n")

    def fake_run(command, cwd, stdout, stderr, check):
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/bin/docker" if name == "docker" else None
    )

    backend = ContainerBackend(runtime="docker", image="conceptlab/nextgenpb:latest")
    try:
        backend.run(prm_f=prmfile, workdir=tmp_path, nproc=1, ngpb_binary="ngpb")
    except subprocess.CalledProcessError as exc:
        assert exc.returncode == 7
    else:
        raise AssertionError("ContainerBackend should raise on non-zero exit")


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
        "shutil.which", lambda name: "/usr/bin/docker" if name == "docker" else None
    )

    backend = ContainerBackend(
        runtime="docker", image="conceptlab/nextgenpb:latest", stream_output=True
    )
    try:
        backend.run(prm_f=prmfile, workdir=tmp_path, nproc=1, ngpb_binary="ngpb")
    except subprocess.CalledProcessError as exc:
        assert exc.returncode == 9
    else:
        raise AssertionError("ContainerBackend should raise on non-zero streamed exit")


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

    results: list[str] = []

    def worker():
        results.append(
            container_backend.prepare_container_image(
                "apptainer", "https://example.org/NextGenPB.sif"
            )
        )

    thread = threading.Thread(target=worker)
    thread.start()
    started.wait(timeout=2)

    second_result: list[str] = []

    def second_worker():
        second_result.append(
            container_backend.prepare_container_image(
                "apptainer", "https://example.org/NextGenPB.sif"
            )
        )

    second_thread = threading.Thread(target=second_worker)
    second_thread.start()

    time.sleep(0.2)
    assert call_count == 1
    release.set()
    thread.join()
    second_thread.join()

    assert call_count == 1
    assert results == [str(destination)]
    assert second_result == [str(destination)]
    assert destination.read_text() == "image"
