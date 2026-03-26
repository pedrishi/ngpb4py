# ngpb4py

`ngpb4py` is a Python interface for preparing, running, and parsing
[NextGenPB](https://github.com/concept-lab/NextGenPB) jobs.

The package is intentionally small. It focuses on three tasks:

1. building or loading a `.prm` configuration
2. staging required input files into an isolated run directory
3. turning the solver log and supported output files into structured Python objects

## Core Concepts

### `NgpbConfig`

Represents a NextGenPB configuration in Python. It can be created from defaults,
loaded from an existing `.prm`, updated programmatically, validated, and rendered
back to text.

### `NgpbRunner`

Creates a per-run working directory, stages the `.prm` file plus referenced
inputs, launches the container backend, and returns an `NgpbResult`.

### `NgpbResult`

Collects run metadata, parsed log sections, known output files, and simple
metrics suitable for downstream analysis.

## When To Use It

Use `ngpb4py` when you want a Python-native workflow around NextGenPB without
rewriting solver inputs and outputs by hand for each run.
