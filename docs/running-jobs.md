# Running Jobs

## Basic Execution

```python
from ngpb4py import NgpbConfig, NgpbRunner

config = NgpbConfig.from_prm("options.prm")
result = NgpbRunner(nproc=8).run(config=config)
```

## Working Directories

`workdir` is treated as a scratch parent directory, not the final run directory.
Each call to `run()` creates a unique child directory inside it.

```python
result = NgpbRunner().run(config=config, workdir="scratch", keep_files=True)
print(result.scratch_dir)
print(result.workdir)
```

This makes concurrent runs safer because they do not overwrite each other's
files.

## Verbosity

Wrapper logging can be controlled globally on the runner or per run:

```python
runner = NgpbRunner(verbosity=1)
result = runner.run(config=config, verbose=3)
```

Verbosity levels:

- `0`: warnings and errors only
- `1`: high-level progress messages
- `2`: debug logging from the wrapper
- `3`: debug logging plus streamed backend output

## Container Options

You can customize the runtime invocation:

```python
runner = NgpbRunner(
    container_image="/data/images/NextGenPB.sif",
    container_exec_args=["--containall"],
    container_extra_args=["--silent"],
)
```

Use `container_exec_args` for flags passed to `apptainer exec`, and
`container_extra_args` for flags inserted immediately after the runtime command.
