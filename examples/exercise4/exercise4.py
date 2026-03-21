from __future__ import annotations

import sys
from pathlib import Path

from ngpb4py import NgpbConfig, NgpbRunner
from ngpb4py.inputs import NgpbInputs

DEFAULT_VARIANT = "fine_mesh"
VALID_VARIANTS = ("fine_mesh", "rand_center", "focus")


def build_inputs(variant: str = DEFAULT_VARIANT) -> NgpbInputs:
    if variant not in VALID_VARIANTS:
        valid = ", ".join(VALID_VARIANTS)
        raise ValueError(f"Unknown Exercise 4 variant '{variant}'. Expected one of: {valid}")

    workdir = Path(__file__).resolve().parent
    return NgpbInputs(
        prmfile=workdir / f"{variant}.prm",
        pqrfile=None,
        aux_files=[workdir / "1CCM.pdb", workdir / "radius.siz", workdir / "charge.crg"],
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    variant = args[0] if args else DEFAULT_VARIANT
    inputs = build_inputs(variant)
    workdir = Path(__file__).resolve().parent

    result = NgpbRunner(nproc=4).run(
        config=NgpbConfig.defaults(), pqr=None, workdir=str(workdir), inputs=inputs, verbose=3
    )
    print(result.metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
