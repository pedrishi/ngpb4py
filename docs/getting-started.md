# Getting Started

## Requirements

- Python `3.10+`
- A supported container runtime:
  - `apptainer` or `singularity`
  - `docker`

`NgpbRunner` defaults to the published NextGenPB SIF image and prefers
Apptainer-compatible runtimes. When using a remote SIF image with Apptainer or
Singularity, `ngpb4py` caches the download locally.

## Install The Package

```bash
pip install ngpb4py
```

If you are working from a clone of the repository and want the documentation
and test tooling too:

```bash
uv sync --group dev
```

## First Run

The simplest path is to generate a `.prm` file from the built-in defaults and
provide a PQR file:

```python
from ngpb4py import NgpbConfig, NgpbRunner

config = NgpbConfig.defaults()
runner = NgpbRunner(nproc=4)

result = runner.run(
    config=config,
    pqr="molecule.pqr",
    workdir="/tmp/ngpb-runs",
)

print(result.log.energies.total_electrostatic_energy_kt)
```

## Using A Custom Runtime Or Image

Use `container_runtime` to force a runtime instead of relying on auto-detection:

```python
runner = NgpbRunner(
    container_runtime="docker",
    container_image="ghcr.io/example/nextgenpb:latest",
)
```

For Apptainer installed outside `PATH`, provide an absolute executable path:

```python
runner = NgpbRunner(apptainer_path="/opt/apptainer/bin/apptainer")
```

## Running The Repository Examples

The repository includes exercises under the `examples/` directory:

- `exercise1`
- `exercise2`
- `exercise3`
- `exercise4`

Run them from the repository root:

```bash
python examples/exercise1/exercise1.py
```

## Best Practices

- Use a parent scratch directory such as `/tmp/ngpb-runs` and let `run()` create
  per-run child directories
- Start with `NgpbConfig.defaults()` and layer only the parameters you need to
  change
- Set `keep_files=True` when you are validating new inputs or debugging runtime
  failures
- Use `verbose=2` or `verbose=3` while integrating, then drop back to quieter
  logging for stable workflows
