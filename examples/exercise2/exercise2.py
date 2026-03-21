from pathlib import Path

from ngpb4py import NgpbConfig, NgpbRunner
from ngpb4py.inputs import NgpbInputs

workdir = Path(__file__).resolve().parent
options_prm = workdir / "options.prm"
inputs = NgpbInputs(
    prmfile=options_prm,
    pqrfile=None,
    aux_files=[
        workdir / "1CCM.pdb",
        workdir / "charge.crg",
        workdir / "radius.siz",
    ],
)
result = NgpbRunner(nproc=4).run(
    config=NgpbConfig.defaults(),
    pqr=None,
    workdir=str(workdir),
    inputs=inputs,
    verbose=3,
)

print(result.metrics)
