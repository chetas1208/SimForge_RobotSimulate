"""I/O helpers for JSON, YAML, text, and pandas datasets."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, Path)):
        return str(value)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def write_json(path: str | Path, payload: Any) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return destination


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_text(path: str | Path, payload: str) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(payload, encoding="utf-8")
    return destination


def read_structured_config(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    raw = source.read_text(encoding="utf-8")
    suffix = source.suffix.lower()
    if suffix == ".json":
        return json.loads(raw)
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError(
                "PyYAML is required to read YAML configs. Install it or use JSON instead."
            ) from exc
        return yaml.safe_load(raw) or {}
    raise ValueError(f"Unsupported config file type: {source.suffix}")


def write_dataframe(df, parquet_path: str | Path, csv_path: str | Path) -> None:
    parquet_target = Path(parquet_path)
    csv_target = Path(csv_path)
    parquet_target.parent.mkdir(parents=True, exist_ok=True)
    csv_target.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_target, index=False)
    try:
        df.to_parquet(parquet_target, index=False)
    except Exception:
        # CSV is still written above, so callers remain retry-safe even if parquet support is absent.
        pass
