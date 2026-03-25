# Running Jobs

## Building Configuration

`NgpbConfig` stores parameter data as a mapping keyed by the exact `.prm`
option names used by NextGenPB. The built-in schema mirrors the documented
parameters from the NextGenPB parameter-file guide, including explicit upstream
defaults, basic validation for known option types, and the documented PRM block
metadata for each known key such as `input`, `mesh`, `model`, `surface`, and
`solver`.

```python
from ngpb4py import NgpbConfig

config = NgpbConfig.defaults().with_updates(
    {
        "filetype": "pdb",
        "filename": "protein.pdb",
        "radius_file": "radius.siz",
        "charge_file": "charge.crg",
        "write_pqr": 1,
        "mesh_shape": 0,
        "scale": 3.0,
        "potential_map": 1,
    }
)
```

The built-in schema validates known options before rendering while still
preserving unknown keys loaded from existing `.prm` files:

```python
config.validate()
prm_text = config.to_prm()
```

## Running An Existing `.prm`

When you already have a prepared `.prm` file, load it into `NgpbConfig` and
run it directly. Runtime inputs referenced by keys such as `filename`,
`radius_file`, and `charge_file` are resolved relative to the `.prm` file:

```python
from ngpb4py import NgpbConfig, NgpbRunner

runner = NgpbRunner()
config = NgpbConfig.from_prm("options.prm")

result = runner.run(config=config, workdir="/tmp/ngpb-runs")
```

If `radius_file` or `charge_file` are omitted, `run()` stages packaged defaults
named `radius.siz` and `charge.crg`. If those keys are explicitly provided,
their paths are resolved from the current working directory, absolute path, or
relative to the source `.prm` file. Missing explicit input files still fail
before launching the backend.

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

`ngpb4py` always runs NextGenPB through the built-in container backend. Common
customization points are:

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
- `container_runtime` can be set to `docker`, `apptainer`, or `singularity`
- `container_image` can be a Docker image reference, a local `.sif`, or a
  remote `.sif` URL

## Operational Guidance

- Prefer absolute paths for runtime executables and externally managed files
- Keep auxiliary input filenames unique because staging rejects name conflicts
- Use a stable output prefix if downstream automation depends on generated file
  names
- Disable version probing with `collect_version=False` if `ngpb --version` is
  unavailable in your environment
