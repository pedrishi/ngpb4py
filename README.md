[![PyPI](https://img.shields.io/pypi/v/ngpb4py.svg)](https://pypi.org/project/ngpb4py/) ![GPL-3.0](https://img.shields.io/github/license/pedrishi/ngpb4py)

# ngpb4py

`ngpb4py` is a Python wrapper for running [NextGenPB](https://github.com/concept-lab/NextGenPB)
through a containerized workflow.

It provides:

- a typed configuration object for `.prm` files
- a high-level runner that stages inputs and executes NextGenPB
- structured parsing of key log sections and supported output files

## Installation

If Apptainer is already installed on your system, install the package normally:

```bash
pip install ngpb4py
```

If Apptainer is not installed, prefer the Conda-based setup provided by this
repository so both `ngpb4py` and `apptainer` are installed together:

```bash
wget https://raw.githubusercontent.com/pedrishi/ngpb4py/refs/heads/main/environment.yml
conda env create -f environment.yml
conda activate ngpb4py
```

For development or local docs/testing, install the project with its development dependencies:

```bash
uv sync --group dev
```

`ngpb4py` expects an Apptainer runtime to be available locally.

## Quick Start

Using an existing .prm file:

```python
from ngpb4py import NgpbConfig, NgpbRunner

config = NgpbConfig.from_prm("examples/exercise1/options.prm")
result = NgpbRunner(nproc=4).run(config=config, verbose=1)

print(result.log.energies.total_electrostatic_energy_kt)
```

Or running with defaults directly on a new .pdb file:
```python
from ngpb4py import NgpbRunner

result = NgpbRunner(nproc=4).run(config={"filetype": "pdb", "filename": "examples/simple_4LZT/4LZT.pdb"})

print(result.log.energies.total_electrostatic_energy_kt)
```

## Documentation

Documentation can be found [here](https://pedrishi.github.io/ngpb4py/)

## License

This project is licensed under the [GNU GPL v3.0](LICENSE).

ngpb4py is a separate Python wrapper project. It is not the NextGenPB solver itself, and its license statement applies to the wrapper code in this repository.

[NextGenPB]((https://github.com/concept-lab/NextGenPB)) is the upstream solver project. That project is distributed separately, includes its own copyright notices, and is also marked there as GPL-3.0 licensed.
