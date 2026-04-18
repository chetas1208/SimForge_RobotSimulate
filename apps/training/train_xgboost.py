"""Train XGBoost risk models on the real warehouse LiDAR feature dataset."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
import pickle
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score, roc_auc_score
from sklearn.preprocessing import label_binarize
import xgboost as xgb

from packages.shared_schema import FeatureSchema, encode_feature_frame
from packages.utils import MODELS_DIR, read_json, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train warehouse risk models with XGBoost.")
    parser.add_argument("--dataset", required=True, help="CSV or parquet dataset path")
    parser.add_argument("--feature-schema", required=True)
    parser.add_argument("--artifact-dir", default=None)
    parser.add_argument("--device", default="cuda:0", help="cuda, cuda:0, cuda:1, or cpu")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--task", choices=["binary", "multiclass"], default="binary")
    return parser.parse_args()


def _load_dataset(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if source.suffix == ".parquet":
        return pd.read_parquet(source)
    return pd.read_csv(source)


def _binary_metrics(y_true: pd.Series, probabilities: np.ndarray) -> dict[str, object]:
    predictions = (probabilities >= 0.5).astype(int)
    metrics = {
        "average_precision": float(average_precision_score(y_true, probabilities)),
        "f1": float(f1_score(y_true, predictions)),
        "confusion_matrix": confusion_matrix(y_true, predictions).tolist(),
    }
    try:
        metrics["roc_auc"] = float(roc_auc_score(y_true, probabilities))
    except ValueError:
        metrics["roc_auc"] = None
    return metrics


def _multiclass_metrics(y_true: pd.Series, probabilities: np.ndarray) -> dict[str, object]:
    predictions = probabilities.argmax(axis=1)
    y_true_values = y_true.to_numpy()
    y_true_binarized = label_binarize(y_true_values, classes=[0, 1, 2])
    metrics = {
        "average_precision": float(average_precision_score(y_true_binarized, probabilities, average="macro")),
        "f1": float(f1_score(y_true_values, predictions, average="macro")),
        "confusion_matrix": confusion_matrix(y_true_values, predictions).tolist(),
    }
    try:
        metrics["roc_auc"] = float(roc_auc_score(y_true_binarized, probabilities, average="macro", multi_class="ovr"))
    except ValueError:
        metrics["roc_auc"] = None
    return metrics


def train(args: argparse.Namespace) -> dict[str, str]:
    dataset = _load_dataset(args.dataset)
    schema = FeatureSchema(**read_json(args.feature_schema))
    if "split" not in dataset.columns:
        raise RuntimeError("Dataset must contain train/val/test split assignments")

    train_df = dataset[dataset["split"] == "train"].copy()
    val_df = dataset[dataset["split"] == "val"].copy()
    test_df = dataset[dataset["split"] == "test"].copy()
    if train_df.empty or val_df.empty or test_df.empty:
        raise RuntimeError("Expected non-empty train/val/test splits")

    x_train = encode_feature_frame(train_df, schema)
    x_val = encode_feature_frame(val_df, schema)
    x_test = encode_feature_frame(test_df, schema)

    if args.task == "binary":
        target_column = "risk_label"
        model = xgb.XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            n_estimators=500,
            max_depth=3,
            learning_rate=0.04,
            min_child_weight=10,
            gamma=0.10,
            subsample=0.75,
            colsample_bytree=0.75,
            reg_alpha=0.5,
            reg_lambda=4.0,
            random_state=args.seed,
            tree_method="hist",
            device=args.device,
        )
        model.fit(
            x_train,
            train_df[target_column],
            eval_set=[(x_val, val_df[target_column])],
            verbose=False,
        )
        val_probabilities = model.predict_proba(x_val)[:, 1]
        test_probabilities = model.predict_proba(x_test)[:, 1]
        metrics_payload = {
            "validation": _binary_metrics(val_df[target_column], val_probabilities),
            "test": _binary_metrics(test_df[target_column], test_probabilities),
        }
    else:
        target_column = "risk_level"
        class_count = int(train_df[target_column].nunique())
        model = xgb.XGBClassifier(
            objective="multi:softprob",
            num_class=class_count,
            eval_metric="mlogloss",
            n_estimators=500,
            max_depth=3,
            learning_rate=0.04,
            min_child_weight=10,
            gamma=0.10,
            subsample=0.75,
            colsample_bytree=0.75,
            reg_alpha=0.5,
            reg_lambda=4.0,
            random_state=args.seed,
            tree_method="hist",
            device=args.device,
        )
        model.fit(
            x_train,
            train_df[target_column],
            eval_set=[(x_val, val_df[target_column])],
            verbose=False,
        )
        val_probabilities = model.predict_proba(x_val)
        test_probabilities = model.predict_proba(x_test)
        metrics_payload = {
            "validation": _multiclass_metrics(val_df[target_column], val_probabilities),
            "test": _multiclass_metrics(test_df[target_column], test_probabilities),
        }

    model_version = f"warehouse-risk-{args.task}-{datetime.now(UTC):%Y%m%d%H%M%S}"
    artifact_dir = Path(args.artifact_dir) if args.artifact_dir else MODELS_DIR / model_version
    artifact_dir.mkdir(parents=True, exist_ok=True)

    risk_model_path = artifact_dir / "risk_model.ubj"
    pickle_path = artifact_dir / "model.pkl"
    feature_schema_path = artifact_dir / "feature_schema.json"
    metrics_path = artifact_dir / "metrics.json"
    config_path = artifact_dir / "train_config.json"
    importance_path = artifact_dir / "feature_importance.json"

    booster = model.get_booster()
    booster.save_model(risk_model_path)
    with pickle_path.open("wb") as handle:
        pickle.dump(
            {
                "model": model,
                "schema": schema.model_dump(mode="json"),
                "model_version": model_version,
                "task": args.task,
                "target_column": target_column,
            },
            handle,
        )

    feature_importance = {
        feature_name: float(score)
        for feature_name, score in zip(schema.encoded_columns, model.feature_importances_)
    }

    write_json(feature_schema_path, schema)
    write_json(metrics_path, {
        "model_version": model_version,
        "task": args.task,
        "target_column": target_column,
        "device": args.device,
        **metrics_payload,
    })
    write_json(config_path, {
        "model_version": model_version,
        "task": args.task,
        "target_column": target_column,
        "device": args.device,
        "dataset_path": str(Path(args.dataset).resolve()),
        "feature_schema_path": str(Path(args.feature_schema).resolve()),
        "seed": args.seed,
        "xgboost_params": model.get_xgb_params(),
    })
    write_json(importance_path, feature_importance)

    return {
        "artifact_dir": str(artifact_dir),
        "risk_model_path": str(risk_model_path),
        "model_pickle_path": str(pickle_path),
        "feature_schema_path": str(feature_schema_path),
        "metrics_path": str(metrics_path),
        "train_config_path": str(config_path),
        "feature_importance_path": str(importance_path),
    }


def main() -> None:
    outputs = train(parse_args())
    for key, value in outputs.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
