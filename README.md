[![PyPI](https://img.shields.io/pypi/v/ngpb4py.svg)](https://pypi.org/project/ngpb4py/) ![GPL-3.0](https://img.shields.io/github/license/pedrishi/ngpb4py)

# ngpb4py

`ngpb4py` is a thin Python wrapper for [NextGenPB](https://github.com/concept-lab/NextGenPB).

## Features

- Typed configuration, runner, and result objects
- Container-based execution with Apptainer as the default runtime
- Structured parsing for documented log sections and potential output files
- Per-run scratch directories with automatic cleanup on successful runs

## Installation

To install the latest stable version run:

```sh
pip install ngpb4py
```

> **Warning:** A supported container runtime must be installed on your system. See the [Apptainer installation guide](https://apptainer.org/docs/user/latest/quick_start.html) if you plan to use Apptainer or Singularity.

By default ngpb4py searches your system PATH for the Apptainer executable.

To specify a custom Apptainer path, pass `apptainer_path` to `NgpbRunner`:

```python
runner = NgpbRunner(apptainer_path="/custom/path/to/apptainer")
```

## Quick Start

```python
from ngpb4py import NgpbConfig, NgpbRunner

config = NgpbConfig.from_prm("examples/exercise1/options.prm")
result = NgpbRunner(nproc=16).run(
    config=config,
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

`ngpb4py` always runs NextGenPB in a container. By default, `NgpbRunner` uses
Apptainer with the published SIF image:

<https://github.com/concept-lab/NextGenPB/releases/download/NextGenPB_v1.0.0/NextGenPB.sif>

If you prefer Docker, build or provide a Docker image and pass the image name to
`NgpbRunner`.

If you want to keep using Apptainer or Singularity with a different image, pass
an alternate local or remote `.sif` via `container_image`:

```python
runner = NgpbRunner(
    container_runtime="apptainer",
    container_image="/data/images/NextGenPB-custom.sif",
)
```

Remote `.sif` URLs are downloaded and cached automatically for
Apptainer-compatible runtimes.

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

## Contributing

Clone this repository and run the following from root of the repository:

```sh
# Create and install a virtual environment
uv sync --python 3.10 --all-extras

# Activate the virtual environment
source .venv/bin/activate

# Install the pre-commit hooks
pre-commit install --install-hooks
```

- This project follows the [Conventional Commits](https://www.conventionalcommits.org/) standard to automate [Semantic Versioning](https://semver.org/) and [Keep A Changelog](https://keepachangelog.com/) with [Commitizen](https://github.com/commitizen-tools/commitizen).
- Run `poe` from within the development environment to print a list of [Poe the Poet](https://github.com/nat-n/poethepoet) tasks available to run on this project.
- Run `uv add {package}` from within the development environment to install a run time dependency and add it to `pyproject.toml` and `uv.lock`. Add `--dev` to install a development dependency.
- Run `uv sync --upgrade` from within the development environment to upgrade all dependencies to the latest versions allowed by `pyproject.toml`. Add `--only-dev` to upgrade the development dependencies only.
- Run `cz bump` to bump the package's version, update the `CHANGELOG.md`, and create a git tag. Then push the changes and the git tag with `git push origin main --tags`.

## License

This repository and the published Python package `ngpb4py` are licensed under
the [GNU GPL v3.0](LICENSE).

`ngpb4py` is a separate Python wrapper project. It is not the `NextGenPB`
solver itself, and its license statement applies to the wrapper code in this
repository.

`NextGenPB` is the upstream solver project maintained at
<https://github.com/concept-lab/NextGenPB>. That project is distributed
separately, includes its own copyright notices, and is also marked there as
GPL-3.0 licensed. When you use `ngpb4py`, you should distinguish between:

- `ngpb4py`: this Python wrapper package and repository
- `NextGenPB`: the external solver, container image, documentation, and source
  code provided by the upstream project
