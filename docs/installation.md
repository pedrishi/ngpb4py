# Installation

## Requirements

`ngpb4py` requires:

- Python 3.10 or newer
- an Apptainer runtime available on `PATH`, or an absolute path passed to `NgpbRunner`

The package runs NextGenPB through a container image. The Python package alone is
not sufficient without a working Apptainer installation.

## Install The Package

If Apptainer is already installed on your system, install from PyPI:

```bash
pip install ngpb4py
```

If Apptainer is not installed, prefer the Conda environment included in this
repository so the Python package and runtime are installed together:

```bash
wget https://raw.githubusercontent.com/pedrishi/ngpb4py/refs/heads/main/environment.yml
conda env create -f environment.yml
conda activate ngpb4py
```

For local development, examples, tests, and docs:

```bash
git clone https://github.com/pedrishi/ngpb4py.git
cd ngpb4py
uv sync --group dev
```

## Verify The Runtime

Check the runtime and package import:

```bash
apptainer --version
python -c "import ngpb4py; print('ngpb4py import OK')"
```

## Custom Runtime Path

If Apptainer is not on `PATH`, pass an explicit absolute path:

```python
from ngpb4py import NgpbRunner

runner = NgpbRunner(apptainer_path="/opt/apptainer/bin/apptainer")
```

## Container Images

By default, `NgpbRunner` uses the published NextGenPB `.sif` image. You can
override it with a local file or remote URL:

```python
runner = NgpbRunner(container_image="/data/images/NextGenPB-custom.sif")
```

Remote `.sif` URLs are downloaded and cached automatically when using Apptainer.
