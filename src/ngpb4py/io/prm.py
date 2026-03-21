from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Mapping

if TYPE_CHECKING:
    from ..config import PrmOption


def render_prm(data: Mapping[str, Any], schema: Mapping[str, "PrmOption"]) -> str:
    lines = []
    for key in sorted(data.keys()):
        value = data[key]
        option = schema.get(key)
        unit = f" [{option.unit}]" if option and option.unit else ""
        lines.append(f"{key} = {value}{unit}")
    return "\n".join(lines) + "\n"


def load_prm(path: str) -> Dict[str, Any]:
    parsed: Dict[str, Any] = {}
    with open(path, "r") as handle:
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
    cleaned = value.split()[0]
    for cast in (int, float):
        try:
            return cast(cleaned)
        except ValueError:
            continue
    return cleaned
