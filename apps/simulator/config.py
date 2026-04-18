"""Config loading for the headless simulation pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from packages.shared_schema import ParsedScenario, ScenarioGenerationRequest
from packages.utils import read_structured_config


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class SimulatorSettings:
    default_config_path: str = os.getenv(
        "SIMFORGE_SCENARIO_CONFIG",
        "apps/simulator/configs/warehouse_blind_corner.yaml",
    )
    use_isaac: bool = _env_flag("SIMFORGE_USE_ISAAC", default=False)
    headless: bool = _env_flag("SIMFORGE_HEADLESS", default=True)
    preview_fps: int = int(os.getenv("SIMFORGE_PREVIEW_FPS", "12"))
    preview_stride: int = int(os.getenv("SIMFORGE_PREVIEW_STRIDE", "2"))


def load_generation_request(
    config_path: str | None = None,
    overrides: dict[str, Any] | None = None,
    settings: SimulatorSettings | None = None,
) -> ScenarioGenerationRequest:
    runtime = settings or SimulatorSettings()
    payload: dict[str, Any] = {}
    if config_path or runtime.default_config_path:
        payload.update(read_structured_config(config_path or runtime.default_config_path))
    if overrides:
        payload.update(overrides)
    if "environment" in payload:
        parsed = ParsedScenario(**payload)
        return ScenarioGenerationRequest.from_parsed_scenario(
            parsed,
            job_id=payload.get("job_id"),
            use_isaac=payload.get("use_isaac", runtime.use_isaac),
            headless=payload.get("headless", runtime.headless),
            base_seed=payload.get("base_seed", 42),
            metadata=payload.get("metadata"),
        )
    payload.setdefault("use_isaac", runtime.use_isaac)
    payload.setdefault("headless", runtime.headless)
    return ScenarioGenerationRequest(**payload)
