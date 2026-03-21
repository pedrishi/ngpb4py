# ngpb4py

`ngpb4py` is a thin Python wrapper for [NextGenPB](https://github.com/concept-lab/NextGenPB).

## Features

- Typed configuration, input, runner, and result objects 
- Pluggable execution backends with Apptainer as the default runtime
- Structured parsing for documented log sections and potential output files
- Per-run scratch directories with automatic cleanup on successful runs

## Installation

Install the package from the repository root:

```bash
uv pip install -e .
```

If you prefer `pip`, the equivalent editable install is:

```bash
pip install -e .
```

For contributors who want to run the test suite, install the development
dependencies as well:

```bash
uv sync --group dev
```

## Quick Start

```python
from ngpb4py import NgpbConfig, NgpbRunner

config = NgpbConfig.defaults()
result = NgpbRunner(nproc=16).run(
    config,
    pqr="molecule.pqr",
    workdir="/tmp/ngpb-scratch",
    verbose=3,
)

print(result.log.grid.total_nodes)
print(result.log.energies.total_electrostatic_energy_kt)

phi_surf = result.parsed_outputs["phi_surf.txt"]
if phi_surf:
    print(phi_surf.coordinates[:10])
    print(phi_surf.potentials[:10])
```

## Running Examples

The repository includes runnable examples under `examples/` that mirror the
[NextGenPB tutorial](https://vdiflorio.github.io/nextgenpb_tutorial/docs/tutorial/).

- `examples/exercise1/`
- `examples/exercise2/`
- `examples/exercise3/`
- `examples/exercise4/`

Run an example from the repository root with Python after installing the
package:

```bash
python examples/exercise1/exercise1.py
```


## Testing

The test suite uses `pytest`, which is not installed by default with the base
package. Install the development dependencies first:

```bash
uv sync --group dev
```

Then run the full test suite:

```bash
uv run --group dev python -m pytest
```

## Runtime Backends

By default, `NgpbRunner` uses Apptainer with the published SIF image:

<https://github.com/concept-lab/NextGenPB/releases/download/NextGenPB_v1.0.0/NextGenPB.sif>

If you prefer Docker, build or provide a Docker image and pass the image name to
`NgpbRunner`.

To add flags directly to `apptainer exec`, pass `container_exec_args`:

```python
runner = NgpbRunner(
    nproc=4,
    container_exec_args=["--nv", "--containall"],
)
```

## Working With Results

`NgpbResult` exposes the parsed NextGenPB terminal log through `result.log`.
Each documented section is available as a typed object when present in the
output:

- `result.log.system`
- `result.log.domain`
- `result.log.surface`
- `result.log.grid`
- `result.log.solver`
- `result.log.energies`

Only parsed values are exposed on these section objects. The parser does not
attach raw per-section log text to `result.log.*`.

When NextGenPB writes any of the following files, `NgpbResult` parses them and
exposes them through `result.parsed_outputs`:

- `phi_surf.txt`
- `phi_nodes.txt`
- `phi_on_atoms.txt`

Each parsed file is returned as a `PotentialSampleSet` with:

- `coordinates`: `List[List[float]]`, where each item is `[x, y, z]`
- `potentials`: `List[float]`, where each item matches the corresponding
  coordinate

## Run Behavior and Verbosity

The `workdir` argument is treated as a scratch parent directory. Each call to
`run()` creates a unique child directory so concurrent runs do not collide.

Successful runs are cleaned up by default. To keep generated files, logs, and
staged inputs on disk, pass `keep_files=True`. On failures, the per-run
directory is kept automatically for debugging.

Use the runner `verbose` argument, or set `NgpbRunner(verbosity=...)`, to
control wrapper logging:

- `0`: warnings and errors only
- `1`: high-level run progress
- `2`: debug logging from the wrapper
- `3`: debug logging plus streaming backend output when supported

This affects the wrapper logs printed by `ngpb4py`. Parsed terminal output
remains available afterwards through `result.log`.
