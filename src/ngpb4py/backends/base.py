from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..inputs import NgpbInputs


@dataclass
class ExecutionResult:
    command: list[str]
    stdout_path: Path
    stderr_path: Path
    output_paths: list[Path] | None = None
    container_digest: str | None = None


class NgpbBackend(Protocol):
    name: str

    def run(
        self, inputs: NgpbInputs, workdir: Path, nproc: int, ngpb_binary: str
    ) -> ExecutionResult: ...
