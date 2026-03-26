# Configuration

## `NgpbConfig`

`NgpbConfig` stores option values plus information about where the configuration
came from. It supports two common entry points:

```python
config = NgpbConfig.defaults()
```

```python
config = NgpbConfig.from_prm("options.prm")
```

## Updating Values

Use `with_updates()` to derive a modified configuration:

```python
focused = config.with_updates(
    {
        "surface_type": 0,
        "surface_parameter": 1.4,
        "solver_options": "-i\\ cgs",
    }
)
```

## Validation

`validate()` checks:

- Python value types
- constrained choices for known options
- compatibility with the built-in schema

Rendering a `.prm` through `to_prm()` validates automatically first.

## Input File Resolution

Input-file options such as `filename`, `radius_file`, and `charge_file` are
resolved in this order:

1. absolute path as provided
2. relative to the current working directory
3. relative to the source `.prm` file, when loaded with `from_prm()`

If `radius_file` or `charge_file` are omitted, `ngpb4py` stages packaged default
database files instead.

## Unknown Keys

Unknown `.prm` keys are preserved in `data` and rendered back out. This allows
the wrapper to round-trip solver options that are not yet modeled explicitly in
the built-in schema.
