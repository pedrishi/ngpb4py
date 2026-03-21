from __future__ import annotations

import contextlib
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from ..inputs import NgpbInputs
from .base import ExecutionResult

_LOGGER = logging.getLogger(__name__)


@dataclass
class ContainerBackend:
    name: str = "container"
    image: str = (
        "https://github.com/concept-lab/NextGenPB/releases/download/NextGenPB_v1.0.0/NextGenPB.sif"
    )
    runtime: str | None = "apptainer"
    apptainer_path: str | None = None
    extra_args: list[str] | None = None
    exec_args: list[str] | None = None
    stream_output: bool = False

    def run(
        self, inputs: NgpbInputs, workdir: Path, nproc: int, ngpb_binary: str
    ) -> ExecutionResult:
        runtime = self.runtime or _detect_runtime(self.apptainer_path)
        if not runtime:
            raise RuntimeError("No container runtime detected (docker or apptainer)")
        runtime_cmd = _resolve_runtime_command(runtime, self.apptainer_path)

        resolved_image = _prepare_container_image(runtime, self.image)

        mount_arg, workdir_in_container = _container_mount(runtime, workdir)
        runtime_args = _runtime_args(runtime, nproc)
        base_cmd = _container_base_cmd(
            runtime,
            runtime_cmd,
            resolved_image,
            mount_arg,
            workdir_in_container,
            runtime_args,
            exec_args=self.exec_args,
        )
        command = base_cmd + [ngpb_binary] + inputs.as_args()
        if self.extra_args:
            command[1:1] = self.extra_args

        _LOGGER.debug("Execution command: %s\n", " ".join(command))

        stdout_path = workdir / "ngpb.stdout.log"
        stderr_path = workdir / "ngpb.stderr.log"
        _execute_command(
            command=command,
            workdir=workdir,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stream_output=self.stream_output,
        )

        digest = _container_digest(runtime, resolved_image)
        return ExecutionResult(
            command=command,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            output_paths=_guess_outputs(workdir),
            container_digest=digest,
        )


def _prepare_container_image(runtime: str, image: str) -> str:
    if runtime not in {"apptainer", "singularity"}:
        return image
    if not _is_remote_image(image):
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

    _download_cached_image(image, destination)
    return str(destination)


def _is_remote_image(image: str) -> bool:
    scheme = urlparse(image).scheme.lower()
    return scheme in {"http", "https"}


def _download_cached_image(url: str, destination: Path) -> None:
    with _path_lock(destination):
        if destination.exists() and destination.stat().st_size > 0:
            return
        _download_with_progress(url, destination)


def _download_with_progress(url: str, destination: Path) -> None:
    tmp_destination = destination.with_suffix(destination.suffix + f".{uuid.uuid4().hex}.part")
    stderr_is_tty = hasattr(sys.stderr, "isatty") and bool(sys.stderr.isatty())
    printed_non_tty = False

    try:
        with urlopen(url) as response, tmp_destination.open("wb") as output_file:
            content_length = response.headers.get("Content-Length", "")
            total_bytes = int(content_length) if content_length.isdigit() else None
            downloaded_bytes = 0

            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output_file.write(chunk)
                downloaded_bytes += len(chunk)

                if total_bytes:
                    progress_text = _format_progress_bar(downloaded_bytes, total_bytes)
                else:
                    progress_text = f"Downloading container image: {_format_size(downloaded_bytes)}"

                if stderr_is_tty:
                    sys.stderr.write(f"\r{progress_text}")
                elif not printed_non_tty:
                    sys.stderr.write(progress_text + "\n")
                    printed_non_tty = True
                sys.stderr.flush()

        if stderr_is_tty:
            sys.stderr.write("\n")
            sys.stderr.flush()
        elif total_bytes:
            sys.stderr.write(
                f"Downloaded container image: {_format_size(downloaded_bytes)}/{_format_size(total_bytes)}\n"
            )
            sys.stderr.flush()
        else:
            sys.stderr.write(f"Downloaded container image: {_format_size(downloaded_bytes)}\n")
            sys.stderr.flush()
        tmp_destination.replace(destination)
    finally:
        tmp_destination.unlink(missing_ok=True)


@contextlib.contextmanager
def _path_lock(
    path: Path, timeout_s: float = 300.0, poll_interval_s: float = 0.1
) -> Iterator[None]:
    lock_path = path.with_suffix(path.suffix + ".lock")
    deadline = time.monotonic() + timeout_s

    while True:
        try:
            lock_path.mkdir()
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for cache lock: {lock_path}")
            time.sleep(poll_interval_s)

    try:
        yield
    finally:
        lock_path.rmdir()


def _format_progress_bar(downloaded_bytes: int, total_bytes: int) -> str:
    ratio = min(downloaded_bytes / total_bytes, 1.0)
    width = 30
    filled = int(ratio * width)
    bar = "#" * filled + "-" * (width - filled)
    percent = int(ratio * 100)
    return (
        f"Downloading container image: [{bar}] {percent:3d}% "
        f"({_format_size(downloaded_bytes)}/{_format_size(total_bytes)})"
    )


def _format_size(size_bytes: int) -> str:
    mib = size_bytes / (1024 * 1024)
    return f"{mib:.1f} MiB"


def _detect_runtime(apptainer_path: str | None = None) -> str | None:
    if apptainer_path:
        _validate_apptainer_path(apptainer_path)
        return "apptainer"
    if shutil.which("apptainer"):
        return "apptainer"
    if shutil.which("singularity"):
        return "singularity"
    if shutil.which("docker"):
        return "docker"
    return None


def _resolve_runtime_command(runtime: str, apptainer_path: str | None = None) -> str:
    if runtime == "docker" and not shutil.which("docker"):
        raise RuntimeError("Docker runtime requested but docker was not found in PATH")
    if runtime == "docker":
        return "docker"
    if runtime == "apptainer":
        if apptainer_path:
            return _validate_apptainer_path(apptainer_path)
        if shutil.which("apptainer"):
            return "apptainer"
        _ensure_apptainer_available()
        return "apptainer"
    if runtime == "singularity" and not shutil.which("singularity"):
        raise RuntimeError("Singularity runtime requested but singularity was not found in PATH")
    if runtime == "singularity":
        return "singularity"
    raise RuntimeError(f"Unsupported runtime: {runtime}")


def _validate_apptainer_path(apptainer_path: str) -> str:
    path = Path(apptainer_path).expanduser()
    if not path.is_absolute():
        raise RuntimeError("Custom Apptainer path must be an absolute path to the executable")
    if not path.exists():
        raise RuntimeError(f"Custom Apptainer path does not exist: {path}")
    if path.is_dir():
        raise RuntimeError(
            f"Custom Apptainer path points to a directory, not an executable: {path}"
        )
    if not os.access(path, os.X_OK):
        raise RuntimeError(f"Custom Apptainer path is not executable: {path}")
    return str(path)


def _ensure_apptainer_available() -> None:
    if not _confirm_apptainer_install():
        raise RuntimeError(
            "Apptainer is not installed. Installation was declined; please install it "
            "manually or re-run and accept the prompt."
        )

    missing_deps = _missing_dependencies(["curl", "rpm2cpio", "cpio"])
    if missing_deps:
        hint = _dependency_install_hint()
        raise RuntimeError(
            "Apptainer is missing and required dependencies are not available: "
            f"{', '.join(missing_deps)}. {hint}"
        )

    arch = platform.machine().lower()
    if arch not in {"x86_64", "amd64"}:
        raise RuntimeError(
            "Apptainer auto-install only supports x86_64 pre-built binaries. "
            "Please install Apptainer manually for your architecture."
        )

    local_prefix = _resolve_install_defaults()
    local_prefix.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ngpb4py-apptainer-") as temp_dir:
        temp_path = Path(temp_dir)
        install_script = temp_path / "install-apptainer.sh"
        script_url = "https://raw.githubusercontent.com/apptainer/apptainer/main/tools/install-unprivileged.sh"

        subprocess.run(["curl", "-s", "-o", str(install_script), script_url], check=True)
        subprocess.run(["bash", str(install_script), str(local_prefix)], check=True)

    path_bin = str(local_prefix / "bin")
    os.environ["PATH"] = f"{path_bin}:{os.environ.get('PATH', '')}"

    if not shutil.which("apptainer"):
        raise RuntimeError(
            "Apptainer installation completed, but the binary is still not found. "
            "Ensure the install prefix bin directory is in PATH."
        )

    print(
        "Apptainer installation complete. If this is a new shell, ensure the install "
        "prefix bin directory is in PATH."
    )


def _confirm_apptainer_install() -> bool:
    auto_install = os.environ.get("NGPB_APPTAINER_AUTO_INSTALL", "").strip().lower()
    if auto_install in {"1", "true", "yes", "y"}:
        return True

    if not sys.stdin.isatty():
        return False

    message = (
        "Apptainer was not found in PATH.\n"
        "Would you like ngpb4py to install the unprivileged Apptainer binaries now? "
        "[Y/n]: "
    )
    try:
        response = input(message).strip().lower()
    except EOFError:
        return False
    return response in {"", "y", "yes"}


def _resolve_install_defaults() -> Path:
    prefix_env = os.environ.get("NGPB_APPTAINER_PREFIX", str(Path.home() / ".local"))
    local_prefix = Path(prefix_env).expanduser()

    if not _should_prompt_defaults():
        return local_prefix

    try:
        change = (
            input("Use the default Apptainer install settings (version and prefix)? [Y/n]: ")
            .strip()
            .lower()
        )
    except EOFError:
        return local_prefix

    if change in {"", "y", "yes"}:
        return local_prefix

    try:
        prefix_input = input(f"Install prefix [{local_prefix}]: ").strip()
    except EOFError:
        prefix_input = ""
    if prefix_input:
        local_prefix = Path(prefix_input).expanduser()

    return local_prefix


def _should_prompt_defaults() -> bool:
    auto_install = os.environ.get("NGPB_APPTAINER_AUTO_INSTALL", "").strip().lower()
    if auto_install in {"1", "true", "yes", "y"}:
        return False
    return sys.stdin.isatty()


def _missing_dependencies(dependencies: list[str]) -> list[str]:
    return [dep for dep in dependencies if not shutil.which(dep)]


def _dependency_install_hint() -> str:
    distro_id, distro_like = _read_os_release()
    distro_tokens = set()
    if distro_id:
        distro_tokens.add(distro_id)
    if distro_like:
        distro_tokens.update(token for token in distro_like.split(",") if token)
    if any(token in {"debian", "ubuntu"} for token in distro_tokens):
        return (
            "\nIf you have sudo: apt-get update && apt-get install -y curl rpm2cpio cpio. \n"
            "Without sudo, use a user-space package manager like conda: \n"
            "conda install -c conda-forge curl cpio rpm."
        )
    if any(token in {"fedora", "rhel", "centos"} for token in distro_tokens):
        return (
            "\nIf you have sudo: dnf install -y curl rpm2cpio cpio. \n"
            "Without sudo, use a user-space package manager like conda: \n"
            "conda install -c conda-forge curl cpio rpm."
        )
    return (
        "Install dependencies using your system package manager "
        "or a user-space option like conda (conda install -c conda-forge curl cpio rpm)."
    )


def _read_os_release() -> tuple[str | None, str | None]:
    try:
        data = Path("/etc/os-release").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None, None
    values = {}
    for line in data:
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    distro_id = values.get("ID")
    distro_like = values.get("ID_LIKE")
    if distro_like:
        distro_like = distro_like.replace(" ", ",")
        distro_like = ",".join([token for token in distro_like.split(",") if token])
    return distro_id, distro_like


def _container_mount(runtime: str, workdir: Path) -> tuple[str, str]:
    if runtime == "docker":
        return f"{workdir}:{workdir}", str(workdir)
    return f"{workdir}:{workdir}", str(workdir)


def _container_base_cmd(
    runtime: str,
    runtime_cmd: str,
    image: str,
    mount: str,
    workdir: str,
    runtime_args: list[str],
    exec_args: list[str] | None = None,
) -> list[str]:
    if runtime == "docker":
        return [runtime_cmd, "run", "--rm"] + runtime_args + ["-v", mount, "-w", workdir, image]
    if runtime in {"apptainer", "singularity"}:
        return [runtime_cmd, "exec"] + (exec_args or []) + runtime_args + ["--bind", mount, image]
    raise RuntimeError(f"Unsupported runtime: {runtime}")


def _runtime_args(runtime: str, nproc: int) -> list[str]:
    if runtime == "docker":
        return ["--cpus", str(nproc), "--env", f"NGPB_NPROC={nproc}"]
    if runtime in {"apptainer", "singularity"}:
        return ["--env", f"NGPB_NPROC={nproc}"]
    return []


def _container_digest(runtime: str, image: str) -> str | None:
    try:
        if runtime == "docker":
            output = subprocess.check_output(["docker", "inspect", "--format", "{{.Id}}", image])
            return output.decode().strip()
        if runtime in {"apptainer", "singularity"}:
            return None
    except Exception:
        return None
    return None


def _execute_command(
    command: list[str], workdir: Path, stdout_path: Path, stderr_path: Path, stream_output: bool
) -> None:
    with stdout_path.open("w") as stdout_file, stderr_path.open("w") as stderr_file:
        if not stream_output:
            completed = subprocess.run(
                command, cwd=workdir, stdout=stdout_file, stderr=stderr_file, check=False
            )
            if completed.returncode != 0:
                raise subprocess.CalledProcessError(completed.returncode, command)
            return

        process = subprocess.Popen(
            command,
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        if process.stdout is None or process.stderr is None:
            raise RuntimeError("Failed to capture process output streams")

        stdout_thread = threading.Thread(
            target=_tee_stream, args=(process.stdout, stdout_file, sys.stdout), daemon=True
        )
        stderr_thread = threading.Thread(
            target=_tee_stream, args=(process.stderr, stderr_file, sys.stderr), daemon=True
        )
        stdout_thread.start()
        stderr_thread.start()
        return_code = process.wait()
        stdout_thread.join()
        stderr_thread.join()
        print()
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, command)


def _tee_stream(source, sink, cli_stream) -> None:
    for line in source:
        sink.write(line)
        sink.flush()
        cli_stream.write(line)
        cli_stream.flush()
    source.close()


def _guess_outputs(workdir: Path) -> list[Path]:
    return sorted(workdir.glob("*"))
