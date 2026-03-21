from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class NgpbInputs:
    prmfile: Path
    pqrfile: Optional[Path] = None
    aux_files: List[Path] = field(default_factory=list)

    def as_args(self) -> List[str]:
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
