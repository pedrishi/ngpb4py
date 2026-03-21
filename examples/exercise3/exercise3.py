from pathlib import Path

from ngpb4py import NgpbConfig, NgpbRunner
from ngpb4py.inputs import NgpbInputs

workdir = Path(__file__).resolve().parent
inputs = NgpbInputs(
    prmfile=workdir / "options.prm",
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
    keep_files=False,
)


print(result.log.energies)
phi_surf = result.parsed_outputs["phi_surf.txt"]
if phi_surf:
    print(phi_surf.coordinates[:10])
    print(phi_surf.potentials[:10])
