from __future__ import annotations

import sys
from pathlib import Path

from ngpb4py import NgpbConfig, NgpbRunner

DEFAULT_VARIANT = "fine_mesh"
VALID_VARIANTS = ("fine_mesh", "rand_center", "focus")


def build_config(variant: str = DEFAULT_VARIANT) -> NgpbConfig:
    if variant not in VALID_VARIANTS:
        valid = ", ".join(VALID_VARIANTS)
        raise ValueError(f"Unknown Exercise 4 variant '{variant}'. Expected one of: {valid}")

    workdir = Path(__file__).resolve().parent
    return NgpbConfig.from_prm(str(workdir / f"{variant}.prm"))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    variant = args[0] if args else DEFAULT_VARIANT
    config = build_config(variant)
    workdir = Path(__file__).resolve().parent
    runner = NgpbRunner(nproc=4)

    result = runner.run(config=config, workdir=str(workdir), verbose=3)
    print(result.metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
