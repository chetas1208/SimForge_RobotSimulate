"""Model loading, schema validation, and single-row risk inference helpers."""

from __future__ import annotations

from pathlib import Path
import pickle
from typing import Any

import numpy as np
import xgboost as xgb

from apps.inference.schema_validation import validate_feature_row
from packages.shared_schema import FeatureSchema, RiskLabel, encode_feature_frame, probability_to_risk_label
from packages.utils import read_json


class RiskScoringModel:
    """Loads saved XGBoost artifacts and predicts warehouse risk."""

    def __init__(self, model_dir: str | Path):
        self.model_dir = Path(model_dir)
        self.schema = FeatureSchema(**read_json(self.model_dir / "feature_schema.json"))
        self.train_config = read_json(self.model_dir / "train_config.json")
        self.model_version = str(self.train_config.get("model_version", self.model_dir.name))
        self.task = str(self.train_config.get("task", "binary"))
        self.target_column = str(self.train_config.get("target_column", "risk_label"))
        self._booster = xgb.Booster()
        self._booster.load_model(self.model_dir / "risk_model.ubj")

    @classmethod
    def from_pickle(cls, model_path: str | Path) -> "RiskScoringModel":
        payload = pickle.loads(Path(model_path).read_bytes())
        instance = cls.__new__(cls)
        instance.model_dir = Path(model_path).parent
        instance.schema = FeatureSchema(**payload["schema"])
        instance.train_config = {
            "model_version": payload["model_version"],
            "task": payload.get("task", "binary"),
            "target_column": payload.get("target_column", "risk_label"),
        }
        instance.model_version = payload["model_version"]
        instance.task = payload.get("task", "binary")
        instance.target_column = payload.get("target_column", "risk_label")
        instance._booster = payload["model"].get_booster()
        return instance

    def predict_row(self, feature_row: dict[str, Any]) -> float:
        prediction = self.predict_detail(feature_row)
        return prediction["risk_score"]

    def predict_detail(self, feature_row: dict[str, Any]) -> dict[str, Any]:
        normalized = validate_feature_row(feature_row, self.schema)
        encoded = encode_feature_frame(normalized, self.schema)
        matrix = xgb.DMatrix(encoded, feature_names=self.schema.encoded_columns)
        raw_prediction = self._booster.predict(matrix)
        if self.task == "multiclass":
            probabilities = np.asarray(raw_prediction[0], dtype=float)
            class_index = int(probabilities.argmax())
            score = float(probabilities[-1] if probabilities.size >= 3 else probabilities.max())
            label = {
                0: RiskLabel.SAFE,
                1: RiskLabel.CAUTION,
                2: RiskLabel.HIGH,
            }.get(class_index, RiskLabel.CAUTION)
        else:
            score = float(np.asarray(raw_prediction).reshape(-1)[0])
            label = probability_to_risk_label(score)
        return {
            "risk_score": max(0.0, min(1.0, score)),
            "risk_label": label,
            "normalized_feature_row": normalized,
        }

    def explain(self, feature_row: dict[str, Any], prediction: dict[str, Any]) -> tuple[str, list[str], list[str]]:
        signals: list[str] = []
        if float(feature_row.get("front_clearance_m", 6.0)) < 1.5:
            signals.append(f"front clearance is {feature_row['front_clearance_m']} m")
        if float(feature_row.get("nearest_object_distance_m", 25.0)) < 1.2:
            signals.append(f"nearest object distance is {feature_row['nearest_object_distance_m']} m")
        if float(feature_row.get("path_blockage_score", 0.0)) > 0.55:
            signals.append(f"path blockage score is {feature_row['path_blockage_score']}")
        if float(feature_row.get("congestion_score", 0.0)) > 0.5:
            signals.append(f"congestion score is {feature_row['congestion_score']}")
        if int(feature_row.get("object_count_forklift", 0)) > 0:
            signals.append("forklift traffic is present")
        if int(feature_row.get("object_count_human", 0)) > 0:
            signals.append("pedestrian traffic is present")

        label = prediction["risk_label"]
        explanation = f"{label.value.title()} risk ({prediction['risk_score']:.2%})"
        if signals:
            explanation += f" because {', '.join(signals[:3])}."

        recommendations = [
            "Reduce clutter in the forward corridor",
            "Increase operating clearance before entering the aisle",
            "Lower robot speed for this scenario",
        ]
        if int(feature_row.get("object_count_forklift", 0)) > 0:
            recommendations.append("Separate forklift and robot movement windows")
        if int(feature_row.get("object_count_human", 0)) > 0:
            recommendations.append("Add pedestrian separation or warning controls")
        return explanation, signals, recommendations[:4]


def predict_single_row(model_dir: str | Path, feature_row: dict[str, Any]) -> float:
    model = RiskScoringModel(model_dir=model_dir)
    return model.predict_row(feature_row)

