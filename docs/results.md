# Working With Results

## Result Object

`NgpbRunner.run()` returns an `NgpbResult` containing execution metadata and
parsed solver output.

```python
result = runner.run(config=config, pqr="molecule.pqr", workdir="/tmp/ngpb-runs")

print(result.run_id)
print(result.command)
print(result.stdout_path)
print(result.provenance)
```

Important fields:

- `run_id`: unique identifier for the execution directory
- `workdir`: per-run child directory
- `stdout_path` and `stderr_path`: captured backend logs
- `output_paths`: files discovered after execution
- `parsed_outputs`: parsed numeric data from known potential output files
- `log`: structured representation of the documented terminal log sections
- `metrics`: flattened numeric metrics derived from the parsed log
- `provenance`: backend name, effective command, process count, and optional
  container digest and solver version

## Parsed Log Sections

`result.log` exposes typed section objects when the corresponding sections were
present in the solver output:

- `system`
- `domain`
- `surface`
- `grid`
- `solver`
- `energies`

Example:

```python
if result.log.grid is not None:
    print(result.log.grid.total_nodes)

if result.log.solver is not None:
    print(result.log.solver.iteration_count)
```

The parser is intentionally conservative: missing sections stay `None`, and
only recognized fields are surfaced as structured values.

## Derived Metrics

`NgpbResult.metrics` collects a small set of stable numeric metrics that are
useful for monitoring and regression checks:

- `mesh.elements`
- `mesh.nodes`
- `solver.iterations`
- `energy.total`
- `energy.solvation`
- `energy.coulombic`
- `energy.direct_ionic`

This is a convenience layer over `result.log`, not a separate source of truth.

## Parsed Output Files

If NextGenPB writes any of the following files, `ngpb4py` parses them into
`PotentialSampleSet` objects:

- `phi_surf.txt`
- `phi_nodes.txt`
- `phi_on_atoms.txt`

Each parsed output contains:

- `coordinates`: `list[list[float]]` shaped as `[x, y, z]`
- `potentials`: `list[float]`

Example:

```python
phi_surf = result.parsed_outputs.get("phi_surf.txt")
if phi_surf is not None:
    print(phi_surf.coordinates[:3])
    print(phi_surf.potentials[:3])
```

Only numeric rows with exactly four columns are accepted. Headers, comments,
and malformed rows are skipped.

## Debugging Failed Runs

When a run fails, the work directory is preserved automatically. In that case
the most useful artifacts are usually:

- `result.stdout_path` and `result.stderr_path` for backend and solver output
- `result.workdir` for staged inputs and generated files
- `result.log_excerpt` when you need a quick tail of stdout in application logs
