"""Image dataset loader and preprocessor for warehouse camera data."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterator
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from PIL import Image
import pandas as pd

from packages.utils import DATA_RAW_REAL, DATA_PROCESSED


class WarehouseImageDataset:
    """Load and preprocess warehouse camera images paired with LiDAR scans."""
    
    def __init__(self, image_root: Path, lidar_root: Path):
        self.image_root = Path(image_root)
        self.lidar_root = Path(lidar_root)
        
    def iter_paired_samples(self) -> Iterator[dict]:
        """Yield image-LiDAR pairs matched by timestamp/scan_id."""
        # Assuming images are named like: 000001.jpg, 000002.jpg, etc.
        # And LiDAR scans are: 000001.bin, 000002.bin, etc.
        
        image_files = sorted(self.image_root.glob("*.jpg")) + sorted(self.image_root.glob("*.png"))
        lidar_files = sorted(self.lidar_root.glob("*.bin"))
        
        # Match by filename stem
        image_dict = {f.stem: f for f in image_files}
        lidar_dict = {f.stem: f for f in lidar_files}
        
        common_ids = set(image_dict.keys()) & set(lidar_dict.keys())
        
        for scan_id in sorted(common_ids):
            yield {
                "scan_id": scan_id,
                "image_path": str(image_dict[scan_id]),
                "lidar_path": str(lidar_dict[scan_id]),
            }
    
    def load_image(self, image_path: str | Path, target_size: tuple[int, int] = (224, 224)) -> np.ndarray:
        """Load and preprocess image for CNN input."""
        img = Image.open(image_path).convert("RGB")
        img = img.resize(target_size, Image.Resampling.BILINEAR)
        img_array = np.array(img, dtype=np.float32) / 255.0
        return img_array
    
    def extract_visual_features(self, image_path: str | Path) -> dict:
        """Extract hand-crafted visual features from image."""
        img = Image.open(image_path).convert("RGB")
        img_array = np.array(img, dtype=np.float32) / 255.0
        
        # Lighting quality (average brightness)
        brightness = float(np.mean(img_array))
        
        # Contrast (std of brightness)
        contrast = float(np.std(img_array))
        
        # Color distribution
        r_mean = float(np.mean(img_array[:, :, 0]))
        g_mean = float(np.mean(img_array[:, :, 1]))
        b_mean = float(np.mean(img_array[:, :, 2]))
        
        # Edge density (proxy for clutter)
        gray = np.mean(img_array, axis=2)
        edges = np.abs(np.gradient(gray)[0]) + np.abs(np.gradient(gray)[1])
        edge_density = float(np.mean(edges))
        
        # Darkness regions (occlusion proxy)
        dark_ratio = float(np.mean(img_array < 0.2))
        
        return {
            "brightness": brightness,
            "contrast": contrast,
            "r_mean": r_mean,
            "g_mean": g_mean,
            "b_mean": b_mean,
            "edge_density": edge_density,
            "dark_ratio": dark_ratio,
            "lighting_quality": brightness * contrast,  # Combined metric
            "visual_clutter": edge_density,
            "occlusion_proxy_visual": dark_ratio,
        }


def build_image_feature_dataset(
    image_root: str | Path,
    lidar_root: str | Path,
    output_name: str = "warehouse_visual_features",
) -> Path:
    """Build visual feature dataset from warehouse images."""
    dataset = WarehouseImageDataset(image_root, lidar_root)
    
    rows = []
    for sample in dataset.iter_paired_samples():
        features = dataset.extract_visual_features(sample["image_path"])
        features["scan_id"] = sample["scan_id"]
        features["image_path"] = sample["image_path"]
        features["lidar_path"] = sample["lidar_path"]
        rows.append(features)
    
    df = pd.DataFrame(rows)
    
    output_dir = DATA_PROCESSED / output_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / f"{output_name}.csv"
    df.to_csv(output_path, index=False)
    
    print(f"Extracted visual features from {len(df)} images")
    print(f"Saved to: {output_path}")
    
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract visual features from warehouse images")
    parser.add_argument("--image-root", required=True, help="Path to image directory")
    parser.add_argument("--lidar-root", required=True, help="Path to LiDAR directory")
    parser.add_argument("--output-name", default="warehouse_visual_features", help="Output dataset name")
    return parser.parse_args()


def main():
    args = parse_args()
    build_image_feature_dataset(
        image_root=args.image_root,
        lidar_root=args.lidar_root,
        output_name=args.output_name,
    )


if __name__ == "__main__":
    main()
