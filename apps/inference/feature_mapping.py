"""Map structured scenarios into the real-data model feature schema."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.shared_schema import ObstacleDensityLevel
from packages.utils import read_json


OBSTACLE_DENSITY_FACTOR = {
    ObstacleDensityLevel.LOW.value: 0.25,
    ObstacleDensityLevel.MEDIUM.value: 0.5,
    ObstacleDensityLevel.HIGH.value: 0.8,
}


def map_scenario_config_to_model_features(
    scenario_config: dict[str, Any],
    job_id: str,
    scenario_id: str,
) -> dict[str, Any]:
    environment = str(scenario_config.get("environment_preset", "warehouse_aisle"))
    difficulty = str(scenario_config.get("difficulty", "medium"))
    obstacle_count = int(scenario_config.get("obstacle_count", 2))
    pedestrian_count = int(scenario_config.get("human_count", 0))
    forklift_count = int(scenario_config.get("forklift_count", 0))
    blind_corner = bool(scenario_config.get("blind_corner", False))
    dropped_object = bool(scenario_config.get("dropped_object", False))
    reflective_floor = bool(scenario_config.get("reflective_floor", False))

    if obstacle_count <= 1:
        density_level = ObstacleDensityLevel.LOW.value
    elif obstacle_count <= 3:
        density_level = ObstacleDensityLevel.MEDIUM.value
    else:
        density_level = ObstacleDensityLevel.HIGH.value
    density_factor = OBSTACLE_DENSITY_FACTOR[density_level]

    pallet_count = obstacle_count + (1 if dropped_object else 0)
    vehicle_platform_count = 1 if environment == "loading_zone" else 0
    total_objects = pedestrian_count + forklift_count + pallet_count + vehicle_platform_count

    env_front_clearance = {
        "warehouse_aisle": 4.2,
        "blind_corner_aisle": 2.6,
        "narrow_corridor": 2.0,
        "loading_zone": 4.8,
    }.get(environment, 4.0)
    env_side_clearance = {
        "warehouse_aisle": 2.0,
        "blind_corner_aisle": 1.5,
        "narrow_corridor": 1.2,
        "loading_zone": 2.8,
    }.get(environment, 1.8)

    difficulty_penalty = {
        "easy": 0.25,
        "medium": 0.45,
        "hard": 0.75,
        "critical": 1.0,
    }.get(difficulty, 0.45)

    front_clearance = max(0.45, env_front_clearance - (0.30 * obstacle_count) - (0.40 * forklift_count) - (0.20 * pedestrian_count) - (0.8 if blind_corner else 0.0) - difficulty_penalty)
    left_clearance = max(0.35, env_side_clearance - (0.12 * obstacle_count) - (0.15 * forklift_count))
    right_clearance = max(0.35, env_side_clearance - (0.10 * obstacle_count) - (0.15 * forklift_count))
    nearest_object_distance = max(0.35, front_clearance * 0.72 - (0.15 if dropped_object else 0.0))
    nearest_human_distance = max(0.4, nearest_object_distance - 0.25) if pedestrian_count > 0 else 25.0
    average_obstacle_distance = min(25.0, nearest_object_distance + 1.5 + (1.2 - density_factor))
    free_space_ratio = max(0.05, min(1.0, 0.96 - (0.07 * total_objects) - (0.18 * density_factor) - (0.1 if blind_corner else 0.0)))
    clutter_score = max(0.0, min(1.0, 0.12 + (0.10 * pallet_count) + (0.12 * forklift_count) + (0.22 * density_factor)))
    occlusion_proxy = max(0.0, min(1.0, 0.08 + (0.35 if blind_corner else 0.0) + (0.18 * density_factor) + (0.08 * forklift_count)))
    if reflective_floor:
        occlusion_proxy = min(1.0, occlusion_proxy + 0.04)

    volumes = ([7.0] * forklift_count) + ([1.4] * pallet_count) + ([2.8] * vehicle_platform_count) + ([0.6] * pedestrian_count)
    bbox_volume_mean = sum(volumes) / len(volumes) if volumes else 0.0
    bbox_volume_max = max(volumes) if volumes else 0.0
    object_speed_proxy = (0.18 * pedestrian_count) + (0.65 * forklift_count) + (0.08 if scenario_config.get("crossing_event") else 0.0)
    path_blockage_score = max(0.0, min(1.0, (1.0 - min(front_clearance / 6.0, 1.0)) * 0.45 + (density_factor * 0.35) + (0.08 * forklift_count) + (0.05 * pedestrian_count)))
    congestion_score = max(0.0, min(1.0, (0.25 * min(total_objects / 10.0, 1.0)) + (0.20 * (1.0 - free_space_ratio)) + (0.20 * clutter_score) + (0.20 * path_blockage_score) + (0.15 * min(occlusion_proxy + density_factor, 1.0))))

    return {
        "scan_id": scenario_id,
        "frame_index": int(scenario_config.get("variant_index", 0)),
        "sequence_id": job_id,
        "scan_chunk": f"{job_id}_simulated",
        "environment_type": environment,
        "object_count_total": total_objects,
        "object_count_human": pedestrian_count,
        "object_count_forklift": forklift_count,
        "object_count_pallet": pallet_count,
        "object_count_vehicle_platform": vehicle_platform_count,
        "nearest_object_distance_m": round(nearest_object_distance, 4),
        "nearest_human_distance_m": round(nearest_human_distance, 4),
        "average_obstacle_distance_m": round(average_obstacle_distance, 4),
        "obstacle_density": round(density_factor * max(total_objects, 1), 4),
        "left_clearance_m": round(left_clearance, 4),
        "right_clearance_m": round(right_clearance, 4),
        "front_clearance_m": round(front_clearance, 4),
        "free_space_ratio": round(free_space_ratio, 4),
        "clutter_score": round(clutter_score, 4),
        "occlusion_proxy": round(occlusion_proxy, 4),
        "bbox_volume_mean": round(bbox_volume_mean, 4),
        "bbox_volume_max": round(bbox_volume_max, 4),
        "object_speed_proxy": round(object_speed_proxy, 4),
        "path_blockage_score": round(path_blockage_score, 4),
        "congestion_score": round(congestion_score, 4),
    }


def map_scenario_config_path_to_model_features(
    scenario_config_path: str | Path,
    job_id: str,
    scenario_id: str,
) -> dict[str, Any]:
    return map_scenario_config_to_model_features(read_json(scenario_config_path), job_id=job_id, scenario_id=scenario_id)

