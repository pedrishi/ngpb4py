from pathlib import Path

from ngpb4py import NgpbConfig, NgpbRunner

workdir = Path(__file__).resolve().parent
config = NgpbConfig.from_prm(str(workdir / "options.prm"))
runner = NgpbRunner(nproc=4)
result = runner.run(config=config, workdir=str(workdir), verbose=3)

print(result.metrics)
