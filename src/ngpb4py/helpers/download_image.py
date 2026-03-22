import contextlib
import sys
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from urllib.request import urlopen


def download_cached_image(url: str, destination: Path) -> None:
    with path_lock(destination):
        if destination.exists() and destination.stat().st_size > 0:
            return
        download_with_progress(url, destination)


def download_with_progress(url: str, destination: Path) -> None:
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
                    progress_text = format_progress_bar(downloaded_bytes, total_bytes)
                else:
                    progress_text = f"Downloading container image: {format_size(downloaded_bytes)}"

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
                f"Downloaded container image: {format_size(downloaded_bytes)}/{format_size(total_bytes)}\n"
            )
            sys.stderr.flush()
        else:
            sys.stderr.write(f"Downloaded container image: {format_size(downloaded_bytes)}\n")
            sys.stderr.flush()
        tmp_destination.replace(destination)
    finally:
        tmp_destination.unlink(missing_ok=True)


@contextlib.contextmanager
def path_lock(path: Path, timeout_s: float = 300.0, poll_interval_s: float = 0.1) -> Iterator[None]:
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


def format_progress_bar(downloaded_bytes: int, total_bytes: int) -> str:
    ratio = min(downloaded_bytes / total_bytes, 1.0)
    width = 30
    filled = int(ratio * width)
    bar = "#" * filled + "-" * (width - filled)
    percent = int(ratio * 100)
    return (
        f"Downloading container image: [{bar}] {percent:3d}% "
        f"({format_size(downloaded_bytes)}/{format_size(total_bytes)})"
    )


def format_size(size_bytes: int) -> str:
    mib = size_bytes / (1024 * 1024)
    return f"{mib:.1f} MiB"
