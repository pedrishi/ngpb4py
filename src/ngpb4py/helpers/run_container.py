import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import urlparse

from ngpb4py.helpers.download_image import download_cached_image


def prepare_container_image(runtime: str, image: str) -> str:
    if runtime != "apptainer":
        return image
    if not is_remote_image(image):
        return image

    cache_dir = Path(
        os.environ.get("NGPB_CONTAINER_CACHE_DIR", str(Path.home() / ".cache" / "ngpb4py"))
    ).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)

    parsed = urlparse(image)
    file_name = Path(parsed.path).name or "container.sif"
    destination = cache_dir / file_name

    if destination.exists() and destination.stat().st_size > 0:
        return str(destination)

    download_cached_image(image, destination)
    return str(destination)


def is_remote_image(image: str) -> bool:
    scheme = urlparse(image).scheme.lower()
    return scheme in {"http", "https"}


def detect_runtime(apptainer_path: str | None = None) -> str:
    if apptainer_path:
        validate_apptainer_path(apptainer_path)
        return apptainer_path
    runtime_cmd = shutil.which("apptainer")
    if runtime_cmd:
        return runtime_cmd
    raise RuntimeError("Apptainer runtime was not found in PATH")


def validate_apptainer_path(apptainer_path: str) -> None:
    if not Path(apptainer_path).is_absolute():
        raise RuntimeError("Custom Apptainer path must be an absolute path")


def execute_command(
    command: list[str], workdir: Path, stdout_path: Path, stderr_path: Path, stream_output: bool
) -> None:
    if stream_output:
        execute_command_streaming(command, workdir, stdout_path, stderr_path)
        return

    with (
        stdout_path.open("w", encoding="utf-8") as stdout_file,
        stderr_path.open("w", encoding="utf-8") as stderr_file,
    ):
        completed = subprocess.run(
            command, cwd=workdir, stdout=stdout_file, stderr=stderr_file, check=False
        )
    if completed.returncode != 0:
        raise subprocess.CalledProcessError(completed.returncode, command)


def execute_command_streaming(
    command: list[str], workdir: Path, stdout_path: Path, stderr_path: Path
) -> None:
    with (
        stdout_path.open("w", encoding="utf-8") as stdout_file,
        stderr_path.open("w", encoding="utf-8") as stderr_file,
    ):
        process = subprocess.Popen(  # noqa: S603
            command, cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        threads = [
            threading.Thread(
                target=stream_pipe, args=(process.stdout, stdout_file, sys.stdout), daemon=True
            ),
            threading.Thread(
                target=stream_pipe, args=(process.stderr, stderr_file, sys.stderr), daemon=True
            ),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        returncode = process.wait()
    if returncode != 0:
        raise subprocess.CalledProcessError(returncode, command)


def stream_pipe(pipe, destination_file, destination_stream) -> None:
    if pipe is None:
        return
    for line in pipe:
        destination_file.write(line)
        destination_file.flush()
        destination_stream.write(line)
        destination_stream.flush()


def container_digest(image: str) -> str | None:
    try:
        if Path(image).exists():
            output = subprocess.check_output(["sha256sum", image], stderr=subprocess.DEVNULL)
            return output.decode(errors="replace").split()[0]
    except Exception:
        return None
    return None
