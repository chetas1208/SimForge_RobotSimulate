"""Derived warehouse risk targets from real LiDAR tabular features."""

from __future__ import annotations

from typing import Any


SAFE_FRONT_CLEARANCE_M = 2.5
HIGH_RISK_FRONT_CLEARANCE_M = 1.2
SAFE_NEAREST_OBJECT_M = 1.8
HIGH_RISK_NEAREST_OBJECT_M = 0.9
SAFE_PATH_BLOCKAGE_SCORE = 0.45
HIGH_RISK_PATH_BLOCKAGE_SCORE = 0.72
SAFE_CONGESTION_SCORE = 0.45
HIGH_RISK_CONGESTION_SCORE = 0.68


def derive_risk_targets(feature_row: dict[str, Any]) -> dict[str, int | float]:
    nearest_object = float(feature_row["nearest_object_distance_m"])
    front_clearance = float(feature_row["front_clearance_m"])
    path_blockage = float(feature_row["path_blockage_score"])
    congestion_score = float(feature_row["congestion_score"])
    free_space_ratio = float(feature_row["free_space_ratio"])
    clutter_score = float(feature_row["clutter_score"])
    forklift_count = int(feature_row["object_count_forklift"])

    obstacle_proximity_risk = max(0.0, min(1.0, 1.0 - (nearest_object / 5.0)))

    unsafe_clearance_label = int(
        nearest_object <= SAFE_NEAREST_OBJECT_M
        or front_clearance <= SAFE_FRONT_CLEARANCE_M
        or path_blockage >= SAFE_PATH_BLOCKAGE_SCORE
    )
    congestion_risk_label = int(
        congestion_score >= SAFE_CONGESTION_SCORE
        or free_space_ratio <= 0.55
        or clutter_score >= 0.55
    )

    high_risk = (
        nearest_object <= HIGH_RISK_NEAREST_OBJECT_M
        or front_clearance <= HIGH_RISK_FRONT_CLEARANCE_M
        or path_blockage >= HIGH_RISK_PATH_BLOCKAGE_SCORE
        or congestion_score >= HIGH_RISK_CONGESTION_SCORE
        or (forklift_count > 0 and nearest_object <= 2.0)
    )
    caution_risk = (
        unsafe_clearance_label == 1
        or congestion_risk_label == 1
        or obstacle_proximity_risk >= 0.45
    )

    if high_risk:
        risk_level = 2
    elif caution_risk:
        risk_level = 1
    else:
        risk_level = 0

    return {
        "unsafe_clearance_label": unsafe_clearance_label,
        "congestion_risk_label": congestion_risk_label,
        "obstacle_proximity_risk": round(obstacle_proximity_risk, 4),
        "risk_label": int(risk_level >= 1),
        "risk_level": risk_level,
    }


def label_derivation_explanation() -> dict[str, object]:
    return {
        "binary_target": "risk_label",
        "binary_definition": "1 when a scan is at least caution-risk based on clearance, blockage, congestion, or proximity thresholds derived from real LiDAR geometry and 3D boxes.",
        "multiclass_target": "risk_level",
        "multiclass_levels": {
            "0": "safe",
            "1": "caution",
            "2": "high",
        },
        "thresholds": {
            "safe_front_clearance_m": SAFE_FRONT_CLEARANCE_M,
            "high_risk_front_clearance_m": HIGH_RISK_FRONT_CLEARANCE_M,
            "safe_nearest_object_m": SAFE_NEAREST_OBJECT_M,
            "high_risk_nearest_object_m": HIGH_RISK_NEAREST_OBJECT_M,
            "safe_path_blockage_score": SAFE_PATH_BLOCKAGE_SCORE,
            "high_risk_path_blockage_score": HIGH_RISK_PATH_BLOCKAGE_SCORE,
            "safe_congestion_score": SAFE_CONGESTION_SCORE,
            "high_risk_congestion_score": HIGH_RISK_CONGESTION_SCORE,
        },
        "limitations": [
            "The public dataset does not include human annotations in its current release, so human-specific training features are zero-filled.",
            "Risk targets are derived heuristically from real geometry and annotations, not from manual safety incident labels.",
        ],
    }

