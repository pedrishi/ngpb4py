from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class NgpbInputs:
    prmfile: Path
    pqrfile: Path | None = None
    aux_files: list[Path] = field(default_factory=list)

    def as_args(self) -> list[str]:
        args = ["--prmfile", str(self.prmfile)]
        if self.pqrfile:
            args += ["--pqrfile", str(self.pqrfile)]
        for path in self.aux_files:
            args.append(str(path))
        return args

    def iter_paths(self) -> Iterable[Path]:
        if self.prmfile:
            yield self.prmfile
        if self.pqrfile:
            yield self.pqrfile
        for path in self.aux_files:
            yield path
