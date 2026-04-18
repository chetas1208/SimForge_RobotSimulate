"""Structured feature extraction from LiDAR scans and 3D bounding boxes."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from apps.training.warehouse_dataset import BoundingBox3D, WarehouseScanRecord


CLASS_MAP = {
    "FTS": "vehicle_platform",
    "ELFplusplus": "vehicle_platform",
    "CargoBike": "vehicle_platform",
    "Box": "pallet",
    "ForkLift": "forklift",
}


@dataclass(frozen=True)
class FeatureExtractionConfig:
    forward_axis: str = "x"
    front_range_m: float = 6.0
    side_range_m: float = 3.5
    corridor_half_width_m: float = 1.6
    occupancy_grid_x_bins: int = 12
    occupancy_grid_y_bins: int = 8


def canonical_class_name(raw: str) -> str:
    return CLASS_MAP.get(raw, raw.lower())


def extract_feature_row(
    record: WarehouseScanRecord,
    previous_record: WarehouseScanRecord | None = None,
    config: FeatureExtractionConfig | None = None,
) -> dict[str, float | int | str]:
    runtime = config or FeatureExtractionConfig()
    points_xy = record.points_xyz[:, :2] if record.points_xyz.size else np.empty((0, 2), dtype=np.float32)
    object_counts = Counter(canonical_class_name(box.class_name) for box in record.boxes)

    object_distances = np.array([box.radial_distance_m for box in record.boxes], dtype=np.float32)
    obstacle_boxes = [box for box in record.boxes if canonical_class_name(box.class_name) != "human"]
    obstacle_distances = np.array([box.radial_distance_m for box in obstacle_boxes], dtype=np.float32)
    volume_values = np.array([box.volume_m3 for box in record.boxes], dtype=np.float32)

    nearest_object_distance = float(object_distances.min()) if object_distances.size else 25.0
    nearest_human_distance = 25.0
    average_obstacle_distance = float(obstacle_distances.mean()) if obstacle_distances.size else 25.0

    left_clearance = _sector_clearance(points_xy, axis="left", runtime=runtime)
    right_clearance = _sector_clearance(points_xy, axis="right", runtime=runtime)
    front_clearance = _sector_clearance(points_xy, axis="front", runtime=runtime)
    free_space_ratio = _free_space_ratio(points_xy, runtime)
    clutter_score = _clutter_score(points_xy, len(record.boxes), runtime)
    occlusion_proxy = _occlusion_proxy(points_xy)
    object_speed_proxy = _object_speed_proxy(record.boxes, previous_record.boxes if previous_record else None)
    path_blockage_score = _path_blockage_score(record.boxes, front_clearance, runtime)

    bbox_volume_mean = float(volume_values.mean()) if volume_values.size else 0.0
    bbox_volume_max = float(volume_values.max()) if volume_values.size else 0.0
    obstacle_density = round(len(record.boxes) / max(runtime.front_range_m * (runtime.corridor_half_width_m * 2.0), 1.0), 4)
    congestion_score = _congestion_score(
        total_objects=len(record.boxes),
        front_clearance_m=front_clearance,
        free_space_ratio=free_space_ratio,
        clutter_score=clutter_score,
        path_blockage_score=path_blockage_score,
    )

    return {
        "scan_id": record.scan_id,
        "frame_index": record.frame_index,
        "sequence_id": record.sequence_id,
        "scan_chunk": record.scan_chunk,
        "environment_type": "warehouse_aisle",
        "object_count_total": len(record.boxes),
        "object_count_human": object_counts.get("human", 0),
        "object_count_forklift": object_counts.get("forklift", 0),
        "object_count_pallet": object_counts.get("pallet", 0),
        "object_count_vehicle_platform": object_counts.get("vehicle_platform", 0),
        "nearest_object_distance_m": round(nearest_object_distance, 4),
        "nearest_human_distance_m": round(nearest_human_distance, 4),
        "average_obstacle_distance_m": round(average_obstacle_distance, 4),
        "obstacle_density": obstacle_density,
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


def _sector_clearance(points_xy: np.ndarray, axis: str, runtime: FeatureExtractionConfig) -> float:
    if points_xy.size == 0:
        return 10.0
    x = points_xy[:, 0]
    y = points_xy[:, 1]
    if axis == "front":
        mask = (x > 0.0) & (np.abs(y) <= runtime.corridor_half_width_m)
        values = x[mask]
    elif axis == "left":
        mask = (y > 0.0) & (x >= -0.5) & (x <= runtime.front_range_m / 2.0)
        values = y[mask]
    else:
        mask = (y < 0.0) & (x >= -0.5) & (x <= runtime.front_range_m / 2.0)
        values = np.abs(y[mask])
    if values.size == 0:
        return 10.0
    return float(np.clip(values.min(), 0.0, 20.0))


def _free_space_ratio(points_xy: np.ndarray, runtime: FeatureExtractionConfig) -> float:
    if points_xy.size == 0:
        return 1.0
    x_bins = np.linspace(0.0, runtime.front_range_m, runtime.occupancy_grid_x_bins + 1)
    y_bins = np.linspace(-runtime.corridor_half_width_m, runtime.corridor_half_width_m, runtime.occupancy_grid_y_bins + 1)
    mask = (
        (points_xy[:, 0] >= 0.0)
        & (points_xy[:, 0] <= runtime.front_range_m)
        & (points_xy[:, 1] >= -runtime.corridor_half_width_m)
        & (points_xy[:, 1] <= runtime.corridor_half_width_m)
    )
    roi = points_xy[mask]
    if roi.size == 0:
        return 1.0
    occupancy = np.zeros((runtime.occupancy_grid_x_bins, runtime.occupancy_grid_y_bins), dtype=np.uint8)
    x_idx = np.clip(np.digitize(roi[:, 0], x_bins) - 1, 0, runtime.occupancy_grid_x_bins - 1)
    y_idx = np.clip(np.digitize(roi[:, 1], y_bins) - 1, 0, runtime.occupancy_grid_y_bins - 1)
    occupancy[x_idx, y_idx] = 1
    return float(1.0 - occupancy.mean())


def _clutter_score(points_xy: np.ndarray, object_count: int, runtime: FeatureExtractionConfig) -> float:
    if points_xy.size == 0:
        return 0.0
    mask = (
        (points_xy[:, 0] >= 0.0)
        & (points_xy[:, 0] <= runtime.front_range_m)
        & (np.abs(points_xy[:, 1]) <= runtime.side_range_m)
    )
    local_points = int(mask.sum())
    point_term = min(1.0, local_points / 3500.0)
    object_term = min(1.0, object_count / 10.0)
    return float(np.clip((0.65 * point_term) + (0.35 * object_term), 0.0, 1.0))


def _occlusion_proxy(points_xy: np.ndarray, bin_count: int = 36) -> float:
    if points_xy.size == 0:
        return 0.0
    front_mask = points_xy[:, 0] > 0.0
    front_points = points_xy[front_mask]
    if front_points.size == 0:
        return 0.0
    angles = np.arctan2(front_points[:, 1], front_points[:, 0])
    distances = np.linalg.norm(front_points, axis=1)
    bins = np.linspace(-np.pi / 2.0, np.pi / 2.0, bin_count + 1)
    near_hits = np.zeros(bin_count, dtype=np.uint8)
    indices = np.clip(np.digitize(angles, bins) - 1, 0, bin_count - 1)
    near_hits[indices[distances < 2.5]] = 1
    return float(near_hits.mean())


def _path_blockage_score(
    boxes: Iterable[BoundingBox3D],
    front_clearance_m: float,
    runtime: FeatureExtractionConfig,
) -> float:
    front_corridor_boxes = 0
    for box in boxes:
        lateral_extent = abs(box.position_y_m) <= runtime.corridor_half_width_m
        in_front = 0.0 <= box.position_x_m <= runtime.front_range_m
        if lateral_extent and in_front:
            front_corridor_boxes += 1
    blockage = min(1.0, front_corridor_boxes / 4.0)
    clearance_penalty = 1.0 - min(1.0, front_clearance_m / runtime.front_range_m)
    return float(np.clip((0.6 * blockage) + (0.4 * clearance_penalty), 0.0, 1.0))


def _object_speed_proxy(
    current_boxes: list[BoundingBox3D],
    previous_boxes: list[BoundingBox3D] | None,
) -> float:
    if not previous_boxes or not current_boxes:
        return 0.0
    previous_by_class: dict[str, list[np.ndarray]] = {}
    for box in previous_boxes:
        previous_by_class.setdefault(canonical_class_name(box.class_name), []).append(box.center_xy)
    speeds: list[float] = []
    for box in current_boxes:
        label = canonical_class_name(box.class_name)
        candidates = previous_by_class.get(label)
        if not candidates:
            continue
        current_center = box.center_xy
        distances = [float(np.linalg.norm(current_center - previous_center)) for previous_center in candidates]
        speeds.append(min(distances))
    if not speeds:
        return 0.0
    return float(np.mean(speeds))


def _congestion_score(
    total_objects: int,
    front_clearance_m: float,
    free_space_ratio: float,
    clutter_score: float,
    path_blockage_score: float,
) -> float:
    object_term = min(1.0, total_objects / 10.0)
    clearance_term = 1.0 - min(1.0, front_clearance_m / 6.0)
    free_space_term = 1.0 - free_space_ratio
    return float(
        np.clip(
            (0.25 * object_term)
            + (0.20 * clearance_term)
            + (0.20 * free_space_term)
            + (0.20 * clutter_score)
            + (0.15 * path_blockage_score),
            0.0,
            1.0,
        )
    )

