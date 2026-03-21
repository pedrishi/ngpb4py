from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Protocol

from ..inputs import NgpbInputs


@dataclass
class ExecutionResult:
    command: List[str]
    stdout_path: Path
    stderr_path: Path
    output_paths: Optional[List[Path]] = None
    container_digest: Optional[str] = None


class NgpbBackend(Protocol):
    name: str

    def run(
        self,
        inputs: NgpbInputs,
        workdir: Path,
        nproc: int,
        ngpb_binary: str,
    ) -> ExecutionResult:
        ...
