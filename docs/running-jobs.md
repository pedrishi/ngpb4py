# Running Jobs

## Building Configuration

`NgpbConfig` stores parameter data as a mapping keyed by the exact `.prm`
option names.

```python
from ngpb4py import NgpbConfig

config = NgpbConfig.defaults().with_updates(
    {
        "mesh.fineness": 3,
        "solver.max_iterations": 300,
        "output.prefix": "protein_a",
    }
)
```

The built-in schema validates known options before rendering:

```python
config.validate()
prm_text = config.to_prm()
```

You can also load an existing parameter file:

```python
config = NgpbConfig.from_prm("options.prm")
```

## Passing Explicit Inputs

When you already have a prepared `.prm` file and additional auxiliary inputs,
build an `NgpbInputs` object and pass it through `run()`:

```python
from pathlib import Path

from ngpb4py import NgpbConfig, NgpbInputs, NgpbRunner

runner = NgpbRunner()
inputs = NgpbInputs(
    prmfile=Path("options.prm"),
    pqrfile=Path("molecule.pqr"),
    aux_files=[Path("radius.siz"), Path("charge.crg")],
)

result = runner.run(
    config=NgpbConfig.defaults(),
    pqr=None,
    inputs=inputs,
    workdir="/tmp/ngpb-runs",
)
```

When `inputs` is provided, `NgpbRunner` stages those files into the run
directory instead of generating `ngpb.prm` from `config`.

## Work Directory Semantics

`workdir` is a parent scratch directory, not the final run directory.
Each call to `run()` creates a unique child directory named with a generated
run id.

This gives two useful properties:

- concurrent runs do not collide
- a failed run can be preserved without affecting later runs

On success, the child directory is removed unless `keep_files=True`. On failure,
the child directory is always kept.

## Logging And Verbosity

Wrapper logging is controlled by `NgpbRunner(verbosity=...)` or the per-run
`verbose=` argument:

- `0`: warnings and errors only
- `1`: high-level progress
- `2`: wrapper debug logging
- `3`: wrapper debug logging plus streamed backend output when available

This setting affects the wrapper logs written to the Python process output. The
parsed NextGenPB log is still available later via `result.log`.

## Runtime Configuration

The default backend is the built-in container backend. Common customization
points are:

```python
runner = NgpbRunner(
    nproc=16,
    ngpb_binary="ngpb",
    container_runtime="apptainer",
    container_exec_args=["--nv"],
    container_extra_args=["--debug"],
)
```

- `container_exec_args` are inserted into the runtime's `exec` invocation
- `container_extra_args` are injected earlier in the full runtime command
- `backend` lets you bypass container execution entirely with a custom backend

## Operational Guidance

- Prefer absolute paths for runtime executables and externally managed files
- Keep auxiliary input filenames unique because staging rejects name conflicts
- Use a stable output prefix if downstream automation depends on generated file
  names
- Disable version probing with `collect_version=False` if `ngpb --version` is
  unavailable in your environment
