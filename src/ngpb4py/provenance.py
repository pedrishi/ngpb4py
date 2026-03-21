from __future__ import annotations

import subprocess


def collect_provenance(
    command: list[str],
    nproc: int,
    backend_name: str,
    container_digest: str | None,
    ngpb_binary: str,
    collect_version: bool = True,
) -> dict[str, str]:
    provenance = {"backend": backend_name, "nproc": str(nproc), "command": " ".join(command)}
    if container_digest:
        provenance["container_digest"] = container_digest
    if collect_version:
        version = _detect_ngpb_version(ngpb_binary)
        if version:
            provenance["ngpb_version"] = version

    return provenance


def _detect_ngpb_version(ngpb_binary: str) -> str | None:
    try:
        output = subprocess.check_output([ngpb_binary, "--version"], stderr=subprocess.STDOUT)
        return output.decode(errors="replace").strip().splitlines()[0]
    except Exception:
        return None
