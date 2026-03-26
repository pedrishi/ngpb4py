# Development

## Local Setup

```bash
uv sync --group dev
pre-commit install --install-hooks
```

## Common Tasks

Run tests:

```bash
poe test
```

Run linting:

```bash
poe lint
```

Build documentation:

```bash
poe docs
```

Serve documentation locally:

```bash
poe docs --serve
```

## Examples

The repository includes runnable examples under `examples/`:

- `exercise1`
- `exercise2`
- `exercise3`
- `exercise4`
- `simple_4LZT`
