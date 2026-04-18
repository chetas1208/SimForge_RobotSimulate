"""Preprocess the public warehouse LiDAR dataset into a tabular training set."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from sklearn.model_selection import train_test_split

from apps.training.feature_extraction import FeatureExtractionConfig, extract_feature_row
from apps.training.risk_labeling import (
    FutureRiskLabelingConfig,
    derive_future_window_targets,
    label_derivation_explanation,
)
from apps.training.warehouse_dataset import iter_dataset_records
from packages.shared_schema import (
    DEFAULTS,
    RANGES,
    TARGET_COLUMNS,
    build_feature_schema,
    infer_categorical_levels,
)
from packages.utils import DATA_PROCESSED, DATA_RAW_REAL, DATA_SPLITS, write_dataframe, write_json


REQUIRED_COLUMNS = {
    "scan_id",
    "frame_index",
    "sequence_id",
    "scan_chunk",
    "environment_type",
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
    "path_blockage_score",
    "congestion_score",
    "unsafe_clearance_label",
    "congestion_risk_label",
    "obstacle_proximity_risk",
    "risk_label",
    "risk_level",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a real-data warehouse risk dataset.")
    parser.add_argument("--dataset-root", default=str(DATA_RAW_REAL / "lidar-warehouse-dataset"))
    parser.add_argument("--dataset-name", default="warehouse_lidar_real_features")
    parser.add_argument("--chunk-size", type=int, default=50)
    parser.add_argument("--future-horizon-frames", type=int, default=10)
    parser.add_argument("--max-scans", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-size", type=float, default=0.7)
    parser.add_argument("--val-size", type=float, default=0.15)
    parser.add_argument("--test-size", type=float, default=0.15)
    return parser.parse_args()


def _fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    for column, default in DEFAULTS.items():
        if column not in df.columns:
            df[column] = default
        df[column] = df[column].fillna(default)
    for column in ("unsafe_clearance_label", "congestion_risk_label", "risk_label", "risk_level"):
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).astype(int)
    if "obstacle_proximity_risk" in df.columns:
        df["obstacle_proximity_risk"] = pd.to_numeric(df["obstacle_proximity_risk"], errors="coerce").fillna(0.0)
    return df


def _filter_out_of_range_rows(df: pd.DataFrame) -> pd.DataFrame:
    valid_mask = pd.Series([True] * len(df), index=df.index)
    for column, (lower, upper) in RANGES.items():
        if column not in df.columns:
            continue
        values = pd.to_numeric(df[column], errors="coerce")
        valid_mask &= values.between(lower, upper, inclusive="both")
    return df[valid_mask].copy()


def _assign_splits(
    df: pd.DataFrame,
    train_size: float,
    val_size: float,
    test_size: float,
    seed: int,
) -> pd.DataFrame:
    if round(train_size + val_size + test_size, 5) != 1.0:
        raise ValueError("train/val/test sizes must sum to 1.0")

    groups = (
        df.groupby("scan_chunk")["risk_label"]
        .max()
        .reset_index()
        .rename(columns={"risk_label": "group_label"})
    )
    stratify = groups["group_label"] if groups["group_label"].nunique() > 1 else None
    train_val_groups, test_groups = train_test_split(
        groups["scan_chunk"],
        test_size=test_size,
        random_state=seed,
        stratify=stratify,
    )
    remaining = groups[groups["scan_chunk"].isin(train_val_groups)]
    remaining_stratify = remaining["group_label"] if remaining["group_label"].nunique() > 1 else None
    val_fraction_of_remaining = val_size / (train_size + val_size)
    train_groups, val_groups = train_test_split(
        remaining["scan_chunk"],
        test_size=val_fraction_of_remaining,
        random_state=seed,
        stratify=remaining_stratify,
    )

    split_map = {group: "train" for group in train_groups}
    split_map.update({group: "val" for group in val_groups})
    split_map.update({group: "test" for group in test_groups})
    df["split"] = df["scan_chunk"].map(split_map).fillna("train")
    return df


def build_real_dataset(
    dataset_root: str | Path,
    dataset_name: str,
    chunk_size: int,
    future_horizon_frames: int,
    max_scans: int | None,
    seed: int,
    train_size: float,
    val_size: float,
    test_size: float,
) -> dict[str, str]:
    runtime = FeatureExtractionConfig()
    labeling_runtime = FutureRiskLabelingConfig(horizon_frames=future_horizon_frames)
    rows: list[dict[str, Any]] = []
    previous_record = None
    for record in iter_dataset_records(dataset_root=dataset_root, chunk_size=chunk_size, limit=max_scans):
        previous_for_record = previous_record if previous_record and previous_record.scan_chunk == record.scan_chunk else None
        features = extract_feature_row(record, previous_record=previous_for_record, config=runtime)
        rows.append(features)
        previous_record = record

    if not rows:
        raise RuntimeError(f"No scans found under {dataset_root}")

    feature_df = pd.DataFrame(rows)
    df = derive_future_window_targets(feature_df, config=labeling_runtime)
    if not REQUIRED_COLUMNS.issubset(df.columns):
        missing = sorted(REQUIRED_COLUMNS.difference(df.columns))
        raise RuntimeError(f"Feature dataset is missing required columns: {missing}")

    df = _fill_missing_values(df)
    df = df.drop_duplicates(subset=["scan_id"]).reset_index(drop=True)
    df = _filter_out_of_range_rows(df)
    df = _assign_splits(df, train_size=train_size, val_size=val_size, test_size=test_size, seed=seed)

    categorical_levels = infer_categorical_levels(df.to_dict(orient="records"))
    feature_schema = build_feature_schema(categorical_levels=categorical_levels)

    processed_dir = DATA_PROCESSED / dataset_name
    split_dir = DATA_SPLITS / dataset_name
    processed_dir.mkdir(parents=True, exist_ok=True)
    split_dir.mkdir(parents=True, exist_ok=True)

    csv_path = processed_dir / f"{dataset_name}.csv"
    parquet_path = processed_dir / f"{dataset_name}.parquet"
    feature_schema_path = processed_dir / "feature_schema.json"
    summary_path = processed_dir / "dataset_summary.json"
    label_derivation_path = processed_dir / "risk_label_derivation.json"

    write_dataframe(df, parquet_path=parquet_path, csv_path=csv_path)
    write_json(feature_schema_path, feature_schema)
    write_json(label_derivation_path, label_derivation_explanation(labeling_runtime))
    write_json(
        summary_path,
        {
            "dataset_name": dataset_name,
            "dataset_root": str(Path(dataset_root).resolve()),
            "row_count": int(len(df)),
            "source_row_count": int(len(feature_df)),
            "dropped_no_future_rows": int(len(feature_df) - len(df)),
            "split_counts": Counter(df["split"]),
            "binary_label_counts": Counter(df["risk_label"]),
            "multiclass_label_counts": Counter(df["risk_level"]),
            "target_columns": list(TARGET_COLUMNS),
            "chunk_size": chunk_size,
            "future_horizon_frames": future_horizon_frames,
        },
    )

    for split_name in ("train", "val", "test"):
        split_frame = df[df["split"] == split_name]
        split_frame.to_csv(split_dir / f"{split_name}.csv", index=False)

    return {
        "csv_path": str(csv_path),
        "parquet_path": str(parquet_path),
        "feature_schema_path": str(feature_schema_path),
        "summary_path": str(summary_path),
        "label_derivation_path": str(label_derivation_path),
        "splits_dir": str(split_dir),
    }


def main() -> None:
    args = parse_args()
    outputs = build_real_dataset(
        dataset_root=args.dataset_root,
        dataset_name=args.dataset_name,
        chunk_size=args.chunk_size,
        future_horizon_frames=args.future_horizon_frames,
        max_scans=args.max_scans,
        seed=args.seed,
        train_size=args.train_size,
        val_size=args.val_size,
        test_size=args.test_size,
    )
    for key, value in outputs.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
