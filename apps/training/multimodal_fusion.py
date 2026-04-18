"""Multi-modal fusion: Combine LiDAR features + vision features for risk prediction."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

from packages.utils import MODELS_DIR, write_json


class MultiModalFusionModel:
    """Combine LiDAR and vision features for enhanced risk prediction."""
    
    def __init__(self, fusion_strategy: str = "late"):
        """
        Args:
            fusion_strategy: 'early' (concatenate features) or 'late' (ensemble predictions)
        """
        self.fusion_strategy = fusion_strategy
        self.lidar_model = None
        self.vision_model = None
        self.fusion_model = None
        self.scaler = StandardScaler()
    
    def train_early_fusion(
        self,
        lidar_features: np.ndarray,
        vision_features: np.ndarray,
        labels: np.ndarray,
        **xgb_params,
    ):
        """Early fusion: concatenate features before training."""
        # Concatenate features
        combined_features = np.hstack([lidar_features, vision_features])
        
        # Normalize
        combined_features = self.scaler.fit_transform(combined_features)
        
        # Train single XGBoost model
        self.fusion_model = xgb.XGBClassifier(**xgb_params)
        self.fusion_model.fit(combined_features, labels)
    
    def train_late_fusion(
        self,
        lidar_features: np.ndarray,
        vision_features: np.ndarray,
        labels: np.ndarray,
        **xgb_params,
    ):
        """Late fusion: train separate models and ensemble predictions."""
        # Train LiDAR model
        self.lidar_model = xgb.XGBClassifier(**xgb_params)
        self.lidar_model.fit(lidar_features, labels)
        
        # Train vision model
        self.vision_model = xgb.XGBClassifier(**xgb_params)
        self.vision_model.fit(vision_features, labels)
    
    def predict(self, lidar_features: np.ndarray, vision_features: np.ndarray) -> np.ndarray:
        """Predict using fusion strategy."""
        if self.fusion_strategy == "early":
            combined = np.hstack([lidar_features, vision_features])
            combined = self.scaler.transform(combined)
            return self.fusion_model.predict_proba(combined)[:, 1]
        else:  # late fusion
            lidar_probs = self.lidar_model.predict_proba(lidar_features)[:, 1]
            vision_probs = self.vision_model.predict_proba(vision_features)[:, 1]
            # Weighted average (can be learned)
            return 0.7 * lidar_probs + 0.3 * vision_probs


def train_multimodal_model(
    lidar_dataset_path: str | Path,
    vision_dataset_path: str | Path,
    output_dir: str | Path,
    fusion_strategy: str = "late",
    device: str = "cpu",
) -> dict:
    """Train multi-modal fusion model."""
    # Load datasets
    lidar_df = pd.read_csv(lidar_dataset_path)
    vision_df = pd.read_csv(vision_dataset_path)
    
    # Merge on scan_id
    merged_df = lidar_df.merge(vision_df, on="scan_id", how="inner")
    
    print(f"Merged dataset: {len(merged_df)} samples")
    
    # Separate features
    lidar_cols = [c for c in lidar_df.columns if c not in ["scan_id", "risk_label", "risk_level", "split"]]
    vision_cols = [c for c in vision_df.columns if c.startswith("vision_") or c in ["brightness", "contrast", "edge_density"]]
    
    X_lidar = merged_df[lidar_cols].values
    X_vision = merged_df[vision_cols].values
    y = merged_df["risk_label"].values
    
    # Split
    X_lidar_train, X_lidar_test, X_vision_train, X_vision_test, y_train, y_test = train_test_split(
        X_lidar, X_vision, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Train model
    model = MultiModalFusionModel(fusion_strategy=fusion_strategy)
    
    xgb_params = {
        "objective": "binary:logistic",
        "n_estimators": 500,
        "max_depth": 3,
        "learning_rate": 0.04,
        "tree_method": "hist",
        "device": device,
    }
    
    if fusion_strategy == "early":
        model.train_early_fusion(X_lidar_train, X_vision_train, y_train, **xgb_params)
    else:
        model.train_late_fusion(X_lidar_train, X_vision_train, y_train, **xgb_params)
    
    # Evaluate
    y_pred = model.predict(X_lidar_test, X_vision_test)
    
    from sklearn.metrics import roc_auc_score, f1_score
    roc_auc = roc_auc_score(y_test, y_pred)
    f1 = f1_score(y_test, (y_pred >= 0.5).astype(int))
    
    print(f"Multi-modal {fusion_strategy} fusion:")
    print(f"  ROC-AUC: {roc_auc:.4f}")
    print(f"  F1 Score: {f1:.4f}")
    
    # Save model
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    import pickle
    model_path = output_dir / "multimodal_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    
    # Save metrics
    metrics = {
        "fusion_strategy": fusion_strategy,
        "roc_auc": float(roc_auc),
        "f1_score": float(f1),
        "n_lidar_features": len(lidar_cols),
        "n_vision_features": len(vision_cols),
        "n_train": len(y_train),
        "n_test": len(y_test),
    }
    write_json(output_dir / "metrics.json", metrics)
    
    return {
        "model_path": str(model_path),
        "metrics": metrics,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train multi-modal fusion model")
    parser.add_argument("--lidar-dataset", required=True, help="Path to LiDAR feature CSV")
    parser.add_argument("--vision-dataset", required=True, help="Path to vision feature CSV")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--fusion", default="late", choices=["early", "late"])
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def main():
    args = parse_args()
    train_multimodal_model(
        lidar_dataset_path=args.lidar_dataset,
        vision_dataset_path=args.vision_dataset,
        output_dir=args.output_dir,
        fusion_strategy=args.fusion,
        device=args.device,
    )


if __name__ == "__main__":
    main()
