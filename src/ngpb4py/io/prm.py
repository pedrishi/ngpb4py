from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..config import PrmOption

_BLOCK_ORDER = ("input", "mesh", "model", "surface", "solver")


def render_prm(data: Mapping[str, Any], schema: Mapping[str, PrmOption]) -> str:
    lines = []
    rendered_keys: set[str] = set()

    for block in _BLOCK_ORDER:
        block_keys = [
            key for key, option in schema.items() if option.block == block and key in data
        ]
        if not block_keys:
            continue

        if lines:
            lines.append("")
        lines.append(f"[{block}]")
        for key in block_keys:
            value = data[key]
            lines.append(f"{key} = {value}")
            rendered_keys.add(key)
        lines.append("[../]")

    unknown_keys = sorted(key for key in data if key not in rendered_keys)
    if unknown_keys and lines:
        lines.append("")
    for key in unknown_keys:
        value = data[key]
        lines.append(f"{key} = {value}")

    return "\n".join(lines) + "\n"


def load_prm(path: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    with open(path) as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if "=" not in line:
                continue
            key, value = [part.strip() for part in line.split("=", 1)]
            parsed[key] = _coerce_value(value)
    return parsed


def _coerce_value(value: str) -> Any:
    cleaned = value.split(maxsplit=1)[0]
    for cast in (int, float):
        try:
            return cast(cleaned)
        except ValueError:
            continue
    return cleaned
