"""Feature constants and encoding helpers for the real-data warehouse risk model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from packages.shared_schema.contracts import FEATURE_SCHEMA_VERSION, FeatureSchema, RiskLabel

if TYPE_CHECKING:
    import pandas as pd


SAFE_PROBABILITY_THRESHOLD = 0.35
HIGH_RISK_PROBABILITY_THRESHOLD = 0.65

GROUP_COLUMNS = ["scan_chunk", "sequence_id"]
TARGET_COLUMNS = ["risk_label", "risk_level", "unsafe_clearance_label"]

DROPPED_COLUMNS = [
    "scan_id",
    "frame_index",
    "sequence_id",
    "scan_chunk",
]

NUMERIC_FEATURES = [
    "object_count_total",
    "object_count_human",
    "object_count_forklift",
    "object_count_pallet",
    "object_count_vehicle_platform",
    "nearest_object_distance_m",
    "nearest_human_distance_m",
    "average_obstacle_distance_m",
    "obstacle_density",
    "left_clearance_m",
    "right_clearance_m",
    "front_clearance_m",
    "free_space_ratio",
    "clutter_score",
    "occlusion_proxy",
    "bbox_volume_mean",
    "bbox_volume_max",
    "object_speed_proxy",
]

CATEGORICAL_FEATURES = [
    "environment_type",
]

DEFAULTS: dict[str, Any] = {
    "environment_type": "warehouse_aisle",
    "object_count_total": 0,
    "object_count_human": 0,
    "object_count_forklift": 0,
    "object_count_pallet": 0,
    "object_count_vehicle_platform": 0,
    "nearest_object_distance_m": 25.0,
    "nearest_human_distance_m": 25.0,
    "average_obstacle_distance_m": 25.0,
    "obstacle_density": 0.0,
    "left_clearance_m": 4.0,
    "right_clearance_m": 4.0,
    "front_clearance_m": 6.0,
    "free_space_ratio": 1.0,
    "clutter_score": 0.0,
    "occlusion_proxy": 0.0,
    "bbox_volume_mean": 0.0,
    "bbox_volume_max": 0.0,
    "object_speed_proxy": 0.0,
    "path_blockage_score": 0.0,
    "congestion_score": 0.0,
}

RANGES = {
    "object_count_total": (0, 100),
    "object_count_human": (0, 20),
    "object_count_forklift": (0, 20),
    "object_count_pallet": (0, 100),
    "object_count_vehicle_platform": (0, 50),
    "nearest_object_distance_m": (0.0, 50.0),
    "nearest_human_distance_m": (0.0, 50.0),
    "average_obstacle_distance_m": (0.0, 50.0),
    "obstacle_density": (0.0, 10.0),
    "left_clearance_m": (0.0, 20.0),
    "right_clearance_m": (0.0, 20.0),
    "front_clearance_m": (0.0, 50.0),
    "free_space_ratio": (0.0, 1.0),
    "clutter_score": (0.0, 1.0),
    "occlusion_proxy": (0.0, 1.0),
    "bbox_volume_mean": (0.0, 200.0),
    "bbox_volume_max": (0.0, 500.0),
    "object_speed_proxy": (0.0, 20.0),
    "path_blockage_score": (0.0, 1.0),
    "congestion_score": (0.0, 1.0),
    "unsafe_clearance_label": (0, 1),
    "congestion_risk_label": (0, 1),
    "obstacle_proximity_risk": (0.0, 1.0),
    "risk_label": (0, 1),
    "risk_level": (0, 2),
}


def _default_levels() -> dict[str, list[str]]:
    return {
        "environment_type": [
            "warehouse_aisle",
            "narrow_corridor",
            "loading_zone",
            "blind_corner_aisle",
        ],
    }


def build_feature_schema(
    categorical_levels: dict[str, list[str]] | None = None,
    version: str = FEATURE_SCHEMA_VERSION,
) -> FeatureSchema:
    levels = categorical_levels or _default_levels()
    encoded_columns = list(NUMERIC_FEATURES)
    for feature in CATEGORICAL_FEATURES:
        for level in levels.get(feature, []):
            encoded_columns.append(f"{feature}__{level}")
    return FeatureSchema(
        version=version,
        numeric_features=list(NUMERIC_FEATURES),
        categorical_features=list(CATEGORICAL_FEATURES),
        categorical_levels=levels,
        encoded_columns=encoded_columns,
        target_columns=list(TARGET_COLUMNS),
        group_columns=list(GROUP_COLUMNS),
        defaults=dict(DEFAULTS),
        ranges=dict(RANGES),
        dropped_columns=list(DROPPED_COLUMNS),
    )


def _ensure_dataframe(rows: "pd.DataFrame | dict[str, Any] | list[dict[str, Any]]") -> "pd.DataFrame":
    import pandas as pd

    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    if isinstance(rows, dict):
        return pd.DataFrame([rows])
    return pd.DataFrame(rows)


def normalize_feature_frame(
    rows: "pd.DataFrame | dict[str, Any] | list[dict[str, Any]]",
    schema: FeatureSchema,
) -> "pd.DataFrame":
    import pandas as pd

    df = _ensure_dataframe(rows)
    for feature, default in schema.defaults.items():
        if feature not in df.columns:
            df[feature] = default
    for feature in schema.numeric_features:
        default = schema.defaults.get(feature, 0)
        df[feature] = pd.to_numeric(df[feature], errors="coerce").fillna(default)
    for feature in schema.categorical_features:
        default = str(schema.defaults.get(feature, "unknown"))
        df[feature] = df[feature].fillna(default).astype(str)
    return df


def encode_feature_frame(
    rows: "pd.DataFrame | dict[str, Any] | list[dict[str, Any]]",
    schema: FeatureSchema,
) -> "pd.DataFrame":
    import pandas as pd

    df = normalize_feature_frame(rows, schema)
    encoded = pd.DataFrame(index=df.index)
    for feature in schema.numeric_features:
        encoded[feature] = df[feature]
    for feature in schema.categorical_features:
        values = df[feature].astype(str)
        for level in schema.categorical_levels.get(feature, []):
            encoded[f"{feature}__{level}"] = (values == level).astype(int)
    for column in schema.encoded_columns:
        if column not in encoded.columns:
            encoded[column] = 0
    return encoded[schema.encoded_columns]


def infer_categorical_levels(records: Iterable[dict[str, Any]]) -> dict[str, list[str]]:
    import pandas as pd

    df = pd.DataFrame(list(records))
    levels = _default_levels()
    if df.empty:
        return levels
    for feature in CATEGORICAL_FEATURES:
        if feature in df.columns:
            observed = sorted({str(value) for value in df[feature].dropna().tolist()})
            if observed:
                levels[feature] = observed
    return levels


def probability_to_risk_label(probability: float) -> RiskLabel:
    if probability >= HIGH_RISK_PROBABILITY_THRESHOLD:
        return RiskLabel.HIGH
    if probability >= SAFE_PROBABILITY_THRESHOLD:
        return RiskLabel.CAUTION
    return RiskLabel.SAFE
