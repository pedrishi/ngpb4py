# Getting Started

## Requirements

- Python `3.10+`
- `apptainer`

`NgpbRunner` defaults to the published NextGenPB SIF image. When using a
remote SIF image with Apptainer, `ngpb4py` caches the download locally.

## Install The Package

On Linux, prefer the Conda environment included in this repository so both
`ngpb4py` and `apptainer` are installed together:

```bash
conda env create -f environment.yml
conda activate ngpb4py
apptainer --version
python -c "import ngpb4py; print('ngpb4py import OK')"
```

The Conda environment uses `conda-forge` for `apptainer`, which is currently
available on Linux platforms. If Conda-provided Apptainer is not available on
your platform, install `ngpb4py` with `pip` and set up Apptainer separately:

```bash
pip install ngpb4py
```

If you are working from a clone of the repository and want the documentation
and test tooling too, keep using the existing `uv` development workflow:

```bash
uv sync --group dev
```

## First Run

The simplest path is to load an existing `.prm` file and let `NgpbConfig`
stage the neighboring runtime inputs it references:

```python
from ngpb4py import NgpbConfig, NgpbRunner

config = NgpbConfig.from_prm("examples/exercise1/options.prm")
runner = NgpbRunner(nproc=4)

result = runner.run(config=config, workdir="/tmp/ngpb-runs")

print(result.log.energies.total_electrostatic_energy_kt)
```

## Using A Custom Image

```python
runner = NgpbRunner(
    container_image="/data/images/NextGenPB-custom.sif",
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

- Omit `workdir` to use the current working directory as the scratch parent, or
  pass a relative/absolute parent path such as `/tmp/ngpb-runs`
- Start with `NgpbConfig.defaults()` when you want the upstream
  NextGenPB defaults as a base, then layer only the parameters you need to
  change
- Use `NgpbConfig.from_prm("options.prm")` when you already have a prepared
  parameter file and its referenced inputs
- Set `keep_files=True` when you are validating new inputs or debugging runtime
  failures
- Use `verbose=2` or `verbose=3` while integrating, then drop back to quieter
  logging for stable workflows
