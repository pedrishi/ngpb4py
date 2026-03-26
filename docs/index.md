# ngpb4py

`ngpb4py` is a thin Python wrapper around
[NextGenPB](https://github.com/concept-lab/NextGenPB). It focuses on a small,
typed API for preparing `.prm` inputs with NextGenPB defaults,
running the solver through an Apptainer backend, and parsing the solver
log into structured Python objects.

## What It Provides

- `NgpbConfig` for working with parameter data, loading `.prm` files, and staging referenced inputs
- `NgpbRunner` for creating an isolated run directory and launching NextGenPB
- `NgpbResult` for structured log data, metrics, provenance, and parsed output
  files
- A pluggable backend protocol with a built-in Apptainer implementation

## Typical Workflow

```python
from ngpb4py import NgpbConfig, NgpbRunner

config = NgpbConfig.defaults().with_updates(
    {
        "filetype": "pdb",
        "filename": "protein.pdb",
        "radius_file": "radius.siz",
        "charge_file": "charge.crg",
        "scale": 3.0,
    }
)

runner = NgpbRunner(nproc=8)
result = runner.run(config=config, workdir="/tmp/ngpb-runs", keep_files=False)

print(result.log.grid.total_nodes)
print(result.metrics["energy.total"])
```

## Documentation Guide

- [Getting Started](getting-started.md) explains installation, runtime
  requirements, and the first successful run
- [Running Jobs](running-jobs.md) covers configuration, staged inputs,
  work-directory behavior, and verbosity
- [Working With Results](results.md) explains parsed logs, metrics, provenance,
  and output files
- [Architecture](architecture.md) describes the package layout and extension
  points
- [Reference](reference.md) contains the generated API reference

## Design Principles

- Mirror the documented NextGenPB parameter surface while keeping the Python API explicit
- Prefer typed Python objects over ad hoc text parsing in user code
- Treat each `run()` call as an isolated execution with its own work directory
- Preserve failed runs for debugging and clean up successful runs by default
