"""Adapter that maps backend scenarios to the Track 4 generation and inference service."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.inference.service import ScenarioRiskScoringService
from packages.shared_schema import DifficultyLevel, LightingLevel, ScenarioGenerationRequest


OBSTACLE_LEVEL_MAP = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "extreme": 4,
}


def _infer_difficulty(scenario) -> DifficultyLevel:
    density = scenario.human_crossing_probability + (OBSTACLE_LEVEL_MAP.get(scenario.dropped_obstacle_level, 1) * 0.2)
    if scenario.blocked_aisle_enabled:
        density += 0.2
    if density >= 1.3:
        return DifficultyLevel.CRITICAL
    if density >= 0.95:
        return DifficultyLevel.HARD
    if density >= 0.55:
        return DifficultyLevel.MEDIUM
    return DifficultyLevel.EASY


def build_request_from_scenario(scenario, variant=None, job_id: str | None = None) -> ScenarioGenerationRequest:
    variant_params = getattr(variant, "variant_parameters_json", None) or {}
    obstacle_count = int(variant_params.get("obstacle_count", OBSTACLE_LEVEL_MAP.get(scenario.dropped_obstacle_level, 1)))
    human_present = variant_params.get("human_present")
    if human_present is None:
        human_count = max(0, int(round(scenario.human_crossing_probability * 2)))
    else:
        human_count = 1 if human_present else 0
    forklift_count = 1 if scenario.blocked_aisle_enabled else 0
    reflective_floor = bool(variant_params.get("visibility_modifier", 1.0) < 0.85)
    blind_corner = "blind_corner" in scenario.robot_path_type
    camera_view = scenario.camera_mode
    lighting_value = scenario.lighting_preset
    if lighting_value not in {level.value for level in LightingLevel}:
        lighting_value = LightingLevel.NORMAL.value

    return ScenarioGenerationRequest(
        job_id=job_id or getattr(scenario, "id", None) or "scenario-job",
        scenario_type=scenario.name.lower().replace(" ", "_"),
        environment_preset=scenario.environment_template,
        difficulty=_infer_difficulty(scenario),
        lighting_level=LightingLevel(lighting_value),
        reflective_floor=reflective_floor,
        human_count=human_count,
        obstacle_count=max(0, obstacle_count),
        forklift_count=forklift_count,
        robot_speed_mps=round(1.2 * float(variant_params.get("robot_speed_modifier", 1.0)), 3),
        human_speed_mps=float(variant_params.get("human_speed", 1.0)),
        blind_corner=blind_corner,
        dropped_object=scenario.dropped_obstacle_level != "none",
        crossing_event=bool(variant_params.get("human_present", scenario.human_crossing_probability > 0.2)),
        camera_view=camera_view,
        num_variants=1,
        base_seed=getattr(variant, "deterministic_seed", None) or scenario.random_seed,
        use_isaac=True,
        headless=True,
        metadata={
            "scenario_id": scenario.id,
            "variant_id": getattr(variant, "id", None),
        },
    )


def run_backend_job(scenario, variant, job_id: str, model_dir: str):
    request = build_request_from_scenario(scenario=scenario, variant=variant, job_id=job_id)
    service = ScenarioRiskScoringService(model_dir=model_dir)
    return service.generate_and_score(request)
