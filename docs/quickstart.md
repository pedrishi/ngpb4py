# Quick Start

## Run From An Existing `.prm`

```python
from ngpb4py import NgpbConfig, NgpbRunner

config = NgpbConfig.from_prm("examples/exercise1/options.prm")
runner = NgpbRunner(nproc=4, verbosity=1)
result = runner.run(config=config)

print(result.log.energies.total_electrostatic_energy_kt)
```

## Build A Configuration In Python

```python
from ngpb4py import NgpbConfig, NgpbRunner

config = NgpbConfig.defaults().with_updates(
    {
        "filetype": "pdb",
        "filename": "molecule.pdb",
        "potential_map": 1,
        "surf_write": 1,
    }
)

result = NgpbRunner().run(config=config, keep_files=True)
print(result.log.energies.total_electrostatic_energy_kt)
```

## What Happens During `run()`

1. The configuration is normalized and validated.
2. A unique run directory is created.
3. Referenced input files are copied into that directory.
4. The container backend executes NextGenPB.
5. The terminal log and supported outputs are parsed into `NgpbResult`.

If `keep_files=False`, successful runs are cleaned up automatically. Failed runs
keep their working directory for debugging.
