from __future__ import annotations

import os
import subprocess
from typing import Dict, List, Optional


def collect_provenance(
    command: List[str],
    nproc: int,
    backend_name: str,
    container_digest: Optional[str],
    ngpb_binary: str,
    collect_version: bool = True,
) -> Dict[str, str]:
    provenance = {
        "backend": backend_name,
        "nproc": str(nproc),
        "command": " ".join(command),
    }
    if container_digest:
        provenance["container_digest"] = container_digest
    if collect_version:
        version = _detect_ngpb_version(ngpb_binary)
        if version:
            provenance["ngpb_version"] = version

    return provenance


def _detect_ngpb_version(ngpb_binary: str) -> Optional[str]:
    try:
        output = subprocess.check_output([ngpb_binary, "--version"], stderr=subprocess.STDOUT)
        return output.decode(errors="replace").strip().splitlines()[0]
    except Exception:
        return None
