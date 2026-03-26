# Results

## `NgpbResult`

`NgpbRunner.run()` returns an `NgpbResult` object containing:

- run identifiers and file locations
- the command used to invoke the backend
- parsed log sections
- parsed supported output files
- simple derived metrics
- provenance metadata

## Parsed Log Sections

The parsed log is available at `result.log`. When present in the solver output,
the following sections are mapped to typed objects:

- `result.log.system`
- `result.log.domain`
- `result.log.surface`
- `result.log.grid`
- `result.log.solver`
- `result.log.energies`

Example:

```python
iterations = result.log.solver.iteration_count
nodes = result.log.grid.total_nodes
energy = result.log.energies.total_electrostatic_energy_kt
```

## Parsed Output Files

If these files are produced by NextGenPB, `ngpb4py` parses them automatically:

- `phi_surf.txt`
- `phi_nodes.txt`
- `phi_on_atoms.txt`

Each file is exposed as a `PotentialSampleSet` in `result.parsed_outputs`.

```python
phi_surf = result.parsed_outputs["phi_surf.txt"]
print(phi_surf.coordinates[:3])
print(phi_surf.potentials[:3])
```

## Metrics

`result.metrics` provides a flattened dictionary of commonly useful values, such
as mesh counts, iteration counts, and selected energy terms.
