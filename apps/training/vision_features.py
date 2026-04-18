"""Deep learning vision feature extractor using pre-trained CNNs."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd

# Note: These imports require torch/torchvision or tensorflow
# For MVP, we provide the architecture. Install with:
# pip install torch torchvision

try:
    import torch
    import torchvision.models as models
    import torchvision.transforms as transforms
    from PIL import Image
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("Warning: PyTorch not available. Install with: pip install torch torchvision")


class VisionFeatureExtractor:
    """Extract deep features from images using pre-trained CNN."""
    
    def __init__(self, model_name: str = "resnet50", device: str = "cpu"):
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch is required for vision feature extraction")
        
        self.device = torch.device(device)
        
        # Load pre-trained model
        if model_name == "resnet50":
            self.model = models.resnet50(pretrained=True)
            # Remove final classification layer to get features
            self.model = torch.nn.Sequential(*list(self.model.children())[:-1])
            self.feature_dim = 2048
        elif model_name == "efficientnet_b0":
            self.model = models.efficientnet_b0(pretrained=True)
            self.model = torch.nn.Sequential(*list(self.model.children())[:-1])
            self.feature_dim = 1280
        else:
            raise ValueError(f"Unknown model: {model_name}")
        
        self.model = self.model.to(self.device)
        self.model.eval()
        
        # Standard ImageNet preprocessing
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
    
    def extract_features(self, image_path: str | Path) -> np.ndarray:
        """Extract deep features from a single image."""
        img = Image.open(image_path).convert("RGB")
        img_tensor = self.transform(img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            features = self.model(img_tensor)
        
        # Flatten and convert to numpy
        features = features.squeeze().cpu().numpy()
        return features
    
    def extract_batch(self, image_paths: list[str | Path], batch_size: int = 32) -> np.ndarray:
        """Extract features from multiple images in batches."""
        all_features = []
        
        for i in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[i:i + batch_size]
            batch_tensors = []
            
            for path in batch_paths:
                img = Image.open(path).convert("RGB")
                img_tensor = self.transform(img)
                batch_tensors.append(img_tensor)
            
            batch = torch.stack(batch_tensors).to(self.device)
            
            with torch.no_grad():
                features = self.model(batch)
            
            features = features.squeeze().cpu().numpy()
            all_features.append(features)
        
        return np.vstack(all_features)


def extract_vision_features_dataset(
    image_list_csv: str | Path,
    output_path: str | Path,
    model_name: str = "resnet50",
    device: str = "cpu",
    batch_size: int = 32,
) -> None:
    """Extract vision features for entire dataset."""
    if not TORCH_AVAILABLE:
        print("PyTorch not available. Skipping vision feature extraction.")
        return
    
    # Load image list
    df = pd.read_csv(image_list_csv)
    image_paths = df["image_path"].tolist()
    
    print(f"Extracting features from {len(image_paths)} images using {model_name}...")
    
    extractor = VisionFeatureExtractor(model_name=model_name, device=device)
    features = extractor.extract_batch(image_paths, batch_size=batch_size)
    
    # Create feature dataframe
    feature_cols = [f"vision_feat_{i}" for i in range(features.shape[1])]
    feature_df = pd.DataFrame(features, columns=feature_cols)
    
    # Combine with original metadata
    result_df = pd.concat([df.reset_index(drop=True), feature_df], axis=1)
    
    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, index=False)
    
    print(f"Saved {len(result_df)} samples with {features.shape[1]} vision features to {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract deep vision features using CNN")
    parser.add_argument("--image-list", required=True, help="CSV with image_path column")
    parser.add_argument("--output", required=True, help="Output CSV path")
    parser.add_argument("--model", default="resnet50", choices=["resnet50", "efficientnet_b0"])
    parser.add_argument("--device", default="cpu", help="Device: cpu, cuda, cuda:0, etc.")
    parser.add_argument("--batch-size", type=int, default=32)
    return parser.parse_args()


def main():
    args = parse_args()
    extract_vision_features_dataset(
        image_list_csv=args.image_list,
        output_path=args.output,
        model_name=args.model,
        device=args.device,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
