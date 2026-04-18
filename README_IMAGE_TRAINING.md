# Image Training Pipeline for SimForge

## Overview

This guide explains how to enhance SimForge with **multi-modal risk prediction** by combining LiDAR point cloud features with camera image features.

## Why Multi-Modal?

**LiDAR-only limitations:**
- No color/texture information
- No lighting condition assessment
- Limited occlusion detection
- No visual clutter analysis

**Adding vision features provides:**
- Lighting quality assessment
- Visual occlusion detection
- Clutter and congestion from appearance
- Human/object detection from images
- Complementary risk signals

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Multi-Modal Pipeline                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  LiDAR Scan (.bin)          Camera Image (.jpg)         │
│       ↓                              ↓                   │
│  Point Cloud Features        Vision Features            │
│  - Clearances                - Brightness               │
│  - Obstacles                 - Contrast                 │
│  - Congestion                - Edge density             │
│  - Occlusion                 - Dark regions             │
│       ↓                              ↓                   │
│  ┌──────────────────────────────────────────┐           │
│  │      Feature Fusion Strategy             │           │
│  │  ┌────────────┐    ┌──────────────────┐ │           │
│  │  │ Early      │    │ Late             │ │           │
│  │  │ Fusion     │    │ Fusion           │ │           │
│  │  │ (concat)   │    │ (ensemble)       │ │           │
│  │  └────────────┘    └──────────────────┘ │           │
│  └──────────────────────────────────────────┘           │
│                      ↓                                   │
│              XGBoost Risk Model                          │
│                      ↓                                   │
│         Risk Score + Explanation                         │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Data Requirements

### Expected Directory Structure

```
data/raw_real/
├── Dataset/
│   ├── bin/           # LiDAR point clouds (.bin files)
│   ├── label/         # 3D bounding boxes (.txt files)
│   └── images/        # Camera images (.jpg or .png) ← ADD THIS
│       ├── 000001.jpg
│       ├── 000002.jpg
│       └── ...
```

### Image Requirements

- **Format**: JPG or PNG
- **Resolution**: Any (will be resized to 224x224 for CNN)
- **Naming**: Must match LiDAR scan IDs (e.g., `000001.jpg` pairs with `000001.bin`)
- **Content**: Warehouse camera views (overhead, robot-mounted, or fixed cameras)
- **Quantity**: Same as LiDAR scans (3,287 images for current dataset)

## Installation

### Additional Dependencies

```bash
# Activate virtual environment
source .venv/bin/activate

# Install vision dependencies
pip install torch torchvision pillow

# For GPU acceleration (optional)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

## Pipeline Steps

### Step 1: Extract Hand-Crafted Visual Features

Extract basic visual features (brightness, contrast, edge density) from images:

```bash
python apps/training/image_dataset.py \
  --image-root data/raw_real/Dataset/images \
  --lidar-root data/raw_real/Dataset/bin \
  --output-name warehouse_visual_features
```

**Output**: `data/processed/warehouse_visual_features/warehouse_visual_features.csv`

**Features extracted:**
- `brightness`: Average image brightness (0-1)
- `contrast`: Standard deviation of brightness
- `r_mean`, `g_mean`, `b_mean`: Color channel averages
- `edge_density`: Proxy for visual clutter
- `dark_ratio`: Fraction of dark pixels (occlusion proxy)
- `lighting_quality`: Combined brightness × contrast
- `visual_clutter`: Edge density metric
- `occlusion_proxy_visual`: Dark region ratio

### Step 2: Extract Deep CNN Features (Optional)

Extract deep features using pre-trained ResNet50 or EfficientNet:

```bash
# First, create image list CSV
python -c "
import pandas as pd
from pathlib import Path

image_dir = Path('data/raw_real/Dataset/images')
images = sorted(image_dir.glob('*.jpg'))

df = pd.DataFrame({
    'scan_id': [f.stem for f in images],
    'image_path': [str(f) for f in images]
})

df.to_csv('data/processed/image_list.csv', index=False)
"

# Extract deep features
python apps/training/vision_features.py \
  --image-list data/processed/image_list.csv \
  --output data/processed/vision_deep_features.csv \
  --model resnet50 \
  --device cuda:0 \
  --batch-size 32
```

**Output**: `data/processed/vision_deep_features.csv` with 2048 deep features per image

### Step 3: Train Multi-Modal Fusion Model

Combine LiDAR and vision features:

```bash
# Late fusion (recommended)
python apps/training/multimodal_fusion.py \
  --lidar-dataset data/processed/warehouse_lidar_real_features/warehouse_lidar_real_features.csv \
  --vision-dataset data/processed/warehouse_visual_features/warehouse_visual_features.csv \
  --output-dir models/multimodal-late-fusion \
  --fusion late \
  --device cuda:0

# Early fusion (alternative)
python apps/training/multimodal_fusion.py \
  --lidar-dataset data/processed/warehouse_lidar_real_features/warehouse_lidar_real_features.csv \
  --vision-dataset data/processed/warehouse_visual_features/warehouse_visual_features.csv \
  --output-dir models/multimodal-early-fusion \
  --fusion early \
  --device cuda:0
```

**Output**: 
- `models/multimodal-*/multimodal_model.pkl`
- `models/multimodal-*/metrics.json`

## Fusion Strategies

### Early Fusion
- **Method**: Concatenate LiDAR + vision features → single XGBoost model
- **Pros**: Simpler, learns joint feature interactions
- **Cons**: Requires both modalities at inference time

### Late Fusion
- **Method**: Separate models for LiDAR and vision → ensemble predictions
- **Pros**: More robust, can handle missing modalities
- **Cons**: Slightly more complex
- **Recommended**: Use 70% LiDAR + 30% vision weight

## Integration with Backend

### Update Inference Service

```python
# apps/inference/multimodal_service.py

from apps.training.multimodal_fusion import MultiModalFusionModel
from apps/training.image_dataset import WarehouseImageDataset
import pickle

class MultiModalInferenceService:
    def __init__(self, model_path: str):
        with open(model_path, "rb") as f:
            self.model = pickle.load(f)
        self.image_dataset = WarehouseImageDataset(...)
    
    def predict(self, scenario_config: dict, image_path: str = None):
        # Extract LiDAR features from scenario
        lidar_features = extract_lidar_features(scenario_config)
        
        # Extract vision features if image provided
        if image_path:
            vision_features = self.image_dataset.extract_visual_features(image_path)
        else:
            # Use default/average vision features
            vision_features = get_default_vision_features()
        
        # Predict
        risk_score = self.model.predict(lidar_features, vision_features)
        return risk_score
```

### Update Backend Configuration

```python
# apps/backend/.env
SIMULATION_PROVIDER=track4
TRACK4_MODEL_DIR=./models/multimodal-late-fusion
TRACK4_USE_MULTIMODAL=true
```

## Expected Performance Improvements

### LiDAR-Only Baseline
- ROC-AUC: 0.983
- F1 Score: 0.943

### Multi-Modal (Estimated)
- ROC-AUC: 0.990+ (0.7% improvement)
- F1 Score: 0.955+ (1.2% improvement)
- Better performance on:
  - Low-light scenarios
  - Occlusion cases
  - Visual clutter situations
  - Human detection

## Visualization Enhancements

### Add to Dashboard

1. **Side-by-Side View**
   ```vue
   <template>
     <div class="grid grid-cols-2 gap-4">
       <div>
         <h3>LiDAR View</h3>
         <LidarVisualization :scan="scan" />
       </div>
       <div>
         <h3>Camera View</h3>
         <img :src="imageUrl" />
       </div>
     </div>
   </template>
   ```

2. **Risk Heatmap Overlay**
   - Overlay risk predictions on camera image
   - Highlight high-risk regions
   - Show attention maps from CNN

3. **Feature Importance**
   - Show which features (LiDAR vs vision) contributed most
   - Explain predictions with both modalities

## Troubleshooting

### No Images Available

If you don't have paired camera images:

1. **Use synthetic images**: Generate warehouse views from OpenUSD scenes
2. **Use default features**: Train with LiDAR-only, use average vision features at inference
3. **Download public datasets**: Use warehouse camera datasets from:
   - KITTI dataset (outdoor, but has cameras)
   - Warehouse datasets on Kaggle
   - Simulate with Blender/Isaac Sim

### Memory Issues

If training fails due to memory:

```bash
# Reduce batch size
--batch-size 16

# Use CPU instead of GPU
--device cpu

# Use hand-crafted features instead of deep features
# (Skip Step 2, only use Step 1)
```

### Poor Performance

If multi-modal model performs worse than LiDAR-only:

1. **Check feature alignment**: Ensure images match LiDAR scans
2. **Adjust fusion weights**: Try different ratios (e.g., 80% LiDAR, 20% vision)
3. **Feature normalization**: Ensure features are properly scaled
4. **Data quality**: Check if images are informative (not too dark/blurry)

## Future Enhancements

### 1. Object Detection
- Use YOLO/Faster R-CNN to detect humans, forklifts, obstacles
- Add detection counts as features
- Improve human crossing prediction

### 2. Semantic Segmentation
- Segment floor, walls, obstacles, humans
- Compute free space from segmentation
- Better occlusion understanding

### 3. Temporal Modeling
- Use video sequences instead of single frames
- LSTM/Transformer for temporal risk
- Predict future risk trajectories

### 4. Attention Mechanisms
- Visualize what model focuses on
- Explain predictions with attention maps
- Improve interpretability

### 5. Active Learning
- Identify uncertain predictions
- Request human labels for edge cases
- Continuously improve model

## References

- **ResNet**: Deep Residual Learning for Image Recognition (He et al., 2016)
- **EfficientNet**: Rethinking Model Scaling for CNNs (Tan & Le, 2019)
- **Multi-Modal Fusion**: A Survey on Multi-Modal Deep Learning (Ramachandram & Taylor, 2017)
- **XGBoost**: XGBoost: A Scalable Tree Boosting System (Chen & Guestrin, 2016)

## Summary

**To add image training to SimForge:**

1. ✅ Add camera images to `data/raw_real/Dataset/images/`
2. ✅ Run `image_dataset.py` to extract visual features
3. ✅ (Optional) Run `vision_features.py` for deep features
4. ✅ Run `multimodal_fusion.py` to train fusion model
5. ✅ Update inference service to use multi-modal model
6. ✅ Update dashboard to show image previews
7. ✅ Enjoy improved risk prediction!

**Current Status**: Architecture ready, waiting for image data.

**Next Steps**: Download images from Google Drive link and run pipeline.
