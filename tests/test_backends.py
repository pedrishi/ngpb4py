import io
import subprocess
import threading
import time

from ngpb4py.backends.container import ContainerBackend
from ngpb4py.inputs import NgpbInputs


def test_container_command_building(tmp_path, monkeypatch):
    inputs = NgpbInputs(prmfile=tmp_path / "ngpb.prm")
    inputs.prmfile.write_text("solver.max_iterations = 1\n")

    captured = {}

    def fake_run(command, cwd, stdout, stderr, check):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0)

    def fake_check_output(command):
        return b"sha256:dummy"

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("subprocess.check_output", fake_check_output)

    backend = ContainerBackend(runtime="docker", image="conceptlab/nextgenpb:latest")
    backend.run(inputs=inputs, workdir=tmp_path, nproc=1, ngpb_binary="ngpb")

    assert captured["command"][0:7] == [
        "docker",
        "run",
        "--rm",
        "--cpus",
        "1",
        "--env",
        "NGPB_NPROC=1",
    ]


def test_apptainer_remote_image_download_with_progress(tmp_path, monkeypatch):
    from ngpb4py.backends import container as container_backend

    inputs = NgpbInputs(prmfile=tmp_path / "ngpb.prm")
    inputs.prmfile.write_text("solver.max_iterations = 1\n")

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
    monkeypatch.setattr(container_backend, "urlopen", fake_urlopen)
    monkeypatch.setattr(container_backend.sys, "stderr", fake_stderr)
    monkeypatch.setattr("subprocess.run", fake_run)

    backend = ContainerBackend(
        runtime="apptainer",
        image="https://example.org/NextGenPB.sif",
    )
    backend.run(inputs=inputs, workdir=tmp_path, nproc=1, ngpb_binary="ngpb")

    local_image = tmp_path / "cache" / "NextGenPB.sif"
    assert captured["url"] == "https://example.org/NextGenPB.sif"
    assert str(local_image) in captured["command"]
    assert local_image.exists()
    assert "Downloading container image" in fake_stderr.getvalue()
    assert "100%" in fake_stderr.getvalue()


def test_apptainer_exec_args_are_inserted_after_exec(tmp_path, monkeypatch):
    inputs = NgpbInputs(prmfile=tmp_path / "ngpb.prm")
    inputs.prmfile.write_text("solver.max_iterations = 1\n")

    captured = {}

    def fake_run(command, cwd, stdout, stderr, check):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("subprocess.run", fake_run)

    backend = ContainerBackend(
        runtime="apptainer",
        image="/tmp/NextGenPB.sif",
        exec_args=["--nv", "--containall"],
    )
    backend.run(inputs=inputs, workdir=tmp_path, nproc=2, ngpb_binary="ngpb")

    assert captured["command"][:8] == [
        "apptainer",
        "exec",
        "--nv",
        "--containall",
        "--env",
        "NGPB_NPROC=2",
        "--bind",
        f"{tmp_path}:{tmp_path}",
    ]


def test_container_run_raises_on_nonzero_exit(tmp_path, monkeypatch):
    inputs = NgpbInputs(prmfile=tmp_path / "ngpb.prm")
    inputs.prmfile.write_text("solver.max_iterations = 1\n")

    def fake_run(command, cwd, stdout, stderr, check):
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr("subprocess.run", fake_run)

    backend = ContainerBackend(runtime="docker", image="conceptlab/nextgenpb:latest")
    try:
        backend.run(inputs=inputs, workdir=tmp_path, nproc=1, ngpb_binary="ngpb")
    except subprocess.CalledProcessError as exc:
        assert exc.returncode == 7
    else:
        raise AssertionError("ContainerBackend should raise on non-zero exit")


def test_streaming_container_run_raises_on_nonzero_exit(tmp_path, monkeypatch):
    inputs = NgpbInputs(prmfile=tmp_path / "ngpb.prm")
    inputs.prmfile.write_text("solver.max_iterations = 1\n")

    class FakeProcess:
        def __init__(self):
            self.stdout = io.StringIO("stdout\n")
            self.stderr = io.StringIO("stderr\n")

        def wait(self):
            return 9

    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: FakeProcess())

    backend = ContainerBackend(
        runtime="docker",
        image="conceptlab/nextgenpb:latest",
        stream_output=True,
    )
    try:
        backend.run(inputs=inputs, workdir=tmp_path, nproc=1, ngpb_binary="ngpb")
    except subprocess.CalledProcessError as exc:
        assert exc.returncode == 9
    else:
        raise AssertionError("ContainerBackend should raise on non-zero streamed exit")


def test_apptainer_remote_image_download_is_locked(tmp_path, monkeypatch):
    from ngpb4py.backends import container as container_backend

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

    monkeypatch.setattr(container_backend, "_download_with_progress", fake_download)

    results: list[str] = []

    def worker():
        results.append(container_backend._prepare_container_image("apptainer", "https://example.org/NextGenPB.sif"))

    thread = threading.Thread(target=worker)
    thread.start()
    started.wait(timeout=2)

    second_result: list[str] = []

    def second_worker():
        second_result.append(container_backend._prepare_container_image("apptainer", "https://example.org/NextGenPB.sif"))

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
