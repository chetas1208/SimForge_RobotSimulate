"""Leakage-safe warehouse risk targets derived from future-window outcomes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FutureRiskLabelingConfig:
    """Controls how future-window safety outcomes are derived."""

    horizon_frames: int = 10
    min_future_frames: int = 1
    proximity_high_risk_m: float = 2.9
    proximity_low_risk_m: float = 5.5
    front_clearance_high_risk_m: float = 2.45
    front_clearance_low_risk_m: float = 3.05
    path_blockage_low_risk: float = 0.22
    path_blockage_high_risk: float = 0.46
    congestion_low_risk: float = 0.31
    congestion_high_risk: float = 0.46
    unsafe_clearance_nearest_m: float = 4.0
    unsafe_clearance_front_m: float = 2.7
    unsafe_clearance_path_blockage: float = 0.35
    congestion_alert_score: float = 0.38
    caution_threshold: float = 0.40
    high_threshold: float = 0.68


def _inverse_scale(values: pd.Series, high_risk: float, low_risk: float) -> pd.Series:
    denominator = max(low_risk - high_risk, 1e-6)
    scaled = (low_risk - values.astype(float)) / denominator
    return scaled.clip(lower=0.0, upper=1.0)


def _forward_scale(values: pd.Series, low_risk: float, high_risk: float) -> pd.Series:
    denominator = max(high_risk - low_risk, 1e-6)
    scaled = (values.astype(float) - low_risk) / denominator
    return scaled.clip(lower=0.0, upper=1.0)


def _future_window_stat(
    grouped: pd.core.groupby.generic.SeriesGroupBy,
    horizon_frames: int,
    reducer: str,
) -> pd.Series:
    if reducer not in {"min", "max", "count"}:
        raise ValueError(f"Unsupported reducer: {reducer}")

    def apply_window(series: pd.Series) -> pd.Series:
        shifted = series.shift(-1)
        rolling = shifted.rolling(window=horizon_frames, min_periods=1)
        if reducer == "min":
            reduced = rolling.min()
        elif reducer == "max":
            reduced = rolling.max()
        else:
            reduced = rolling.count()
        return reduced.shift(-(horizon_frames - 1))

    return grouped.transform(apply_window)


def derive_future_window_targets(
    feature_frame: pd.DataFrame,
    config: FutureRiskLabelingConfig | None = None,
) -> pd.DataFrame:
    """Derive predictive labels from future outcomes inside each scan chunk."""

    runtime = config or FutureRiskLabelingConfig()
    df = feature_frame.copy()
    grouped = df.groupby("scan_chunk", sort=False)

    df["future_window_observed_frames"] = _future_window_stat(
        grouped["scan_id"],
        horizon_frames=runtime.horizon_frames,
        reducer="count",
    )
    df["future_min_nearest_object_distance_m"] = _future_window_stat(
        grouped["nearest_object_distance_m"],
        horizon_frames=runtime.horizon_frames,
        reducer="min",
    )
    df["future_min_front_clearance_m"] = _future_window_stat(
        grouped["front_clearance_m"],
        horizon_frames=runtime.horizon_frames,
        reducer="min",
    )
    df["future_max_path_blockage_score"] = _future_window_stat(
        grouped["path_blockage_score"],
        horizon_frames=runtime.horizon_frames,
        reducer="max",
    )
    df["future_max_congestion_score"] = _future_window_stat(
        grouped["congestion_score"],
        horizon_frames=runtime.horizon_frames,
        reducer="max",
    )
    df["future_max_object_count_forklift"] = _future_window_stat(
        grouped["object_count_forklift"],
        horizon_frames=runtime.horizon_frames,
        reducer="max",
    )

    valid_mask = df["future_window_observed_frames"].fillna(0) >= runtime.min_future_frames
    df = df[valid_mask].copy()
    df["future_window_observed_frames"] = df["future_window_observed_frames"].astype(int)

    proximity_component = _inverse_scale(
        df["future_min_nearest_object_distance_m"],
        high_risk=runtime.proximity_high_risk_m,
        low_risk=runtime.proximity_low_risk_m,
    )
    clearance_component = _inverse_scale(
        df["future_min_front_clearance_m"],
        high_risk=runtime.front_clearance_high_risk_m,
        low_risk=runtime.front_clearance_low_risk_m,
    )
    blockage_component = _forward_scale(
        df["future_max_path_blockage_score"],
        low_risk=runtime.path_blockage_low_risk,
        high_risk=runtime.path_blockage_high_risk,
    )
    congestion_component = _forward_scale(
        df["future_max_congestion_score"],
        low_risk=runtime.congestion_low_risk,
        high_risk=runtime.congestion_high_risk,
    )
    forklift_component = df["future_max_object_count_forklift"].clip(lower=0.0, upper=1.0)

    severity_score = (
        (0.30 * proximity_component)
        + (0.30 * clearance_component)
        + (0.20 * blockage_component)
        + (0.15 * congestion_component)
        + (0.05 * forklift_component)
    ).clip(lower=0.0, upper=1.0)

    unsafe_clearance_label = (
        (df["future_min_nearest_object_distance_m"] <= runtime.unsafe_clearance_nearest_m)
        | (df["future_min_front_clearance_m"] <= runtime.unsafe_clearance_front_m)
        | (df["future_max_path_blockage_score"] >= runtime.unsafe_clearance_path_blockage)
    ).astype(int)
    congestion_risk_label = (
        (df["future_max_congestion_score"] >= runtime.congestion_alert_score)
        | (severity_score >= runtime.caution_threshold)
    ).astype(int)
    risk_level = np.where(
        severity_score >= runtime.high_threshold,
        2,
        np.where(severity_score >= runtime.caution_threshold, 1, 0),
    )

    df["unsafe_clearance_label"] = unsafe_clearance_label
    df["congestion_risk_label"] = congestion_risk_label
    df["obstacle_proximity_risk"] = proximity_component.round(4)
    df["future_outcome_severity_score"] = severity_score.round(4)
    df["risk_level"] = risk_level.astype(int)
    df["risk_label"] = (df["risk_level"] >= 1).astype(int)
    return df


def label_derivation_explanation(
    config: FutureRiskLabelingConfig | None = None,
) -> dict[str, object]:
    runtime = config or FutureRiskLabelingConfig()
    return {
        "binary_target": "risk_label",
        "binary_definition": (
            "1 when the next horizon window inside the same scan chunk reaches at least "
            "caution-risk based on future clearance, blockage, and congestion outcomes."
        ),
        "multiclass_target": "risk_level",
        "multiclass_levels": {
            "0": "safe",
            "1": "caution",
            "2": "high",
        },
        "future_window_strategy": {
            "horizon_frames": runtime.horizon_frames,
            "min_future_frames": runtime.min_future_frames,
            "note": (
                "Targets are derived from future outcomes only. Current-frame feature columns remain inputs, "
                "but labels are defined using subsequent frames to reduce same-frame leakage."
            ),
        },
        "severity_formula": {
            "components": {
                "future_min_nearest_object_distance_m": 0.30,
                "future_min_front_clearance_m": 0.30,
                "future_max_path_blockage_score": 0.20,
                "future_max_congestion_score": 0.15,
                "future_max_object_count_forklift": 0.05,
            },
            "thresholds": {
                "caution_threshold": runtime.caution_threshold,
                "high_threshold": runtime.high_threshold,
                "unsafe_clearance_nearest_m": runtime.unsafe_clearance_nearest_m,
                "unsafe_clearance_front_m": runtime.unsafe_clearance_front_m,
                "unsafe_clearance_path_blockage": runtime.unsafe_clearance_path_blockage,
                "congestion_alert_score": runtime.congestion_alert_score,
            },
        },
        "config": asdict(runtime),
        "limitations": [
            "The public dataset does not include human annotations in its current release, so human-specific training features are zero-filled.",
            "Targets are now future-window outcomes, but they are still proxy safety labels derived from geometry and annotations rather than manually curated incident labels.",
            "Rows without any future context inside a scan chunk are dropped from training to keep the target predictive.",
        ],
    }

