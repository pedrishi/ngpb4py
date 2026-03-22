from pathlib import Path

from ngpb4py import NgpbConfig, NgpbRunner

workdir = Path(__file__).resolve().parent
config = NgpbConfig.from_prm(str(workdir / "options.prm"))
runner = NgpbRunner(nproc=4)
result = runner.run(config=config, workdir=str(workdir), verbose=3, keep_files=False)


print(result.log.energies)
phi_surf = result.parsed_outputs["phi_surf.txt"]
if phi_surf:
    print(phi_surf.coordinates[:10])
    print(phi_surf.potentials[:10])
