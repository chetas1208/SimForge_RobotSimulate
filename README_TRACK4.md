# Track 4 Pipeline

This repo now contains a split Track 4 architecture with two separate components:

1. Real-data model training on the public warehouse LiDAR dataset
2. User-description parsing plus OpenUSD/Isaac Sim preview generation

The trained XGBoost model is learned from structured features extracted from real LiDAR scans and 3D bounding boxes. The simulator is used for scenario visualization and preview video generation, not as the primary training source.

## Folder Structure

```text
apps/
  backend/
    app/services/pipeline_service.py
    app/services/text_scenario_service.py
  inference/
    feature_mapping.py
    model.py
    schema_validation.py
    service.py
  parser/
    rule_based.py
    prompt_template.py
    validator.py
    examples.json
  simulator/
    config.py
    isaac_standalone.py
    pipeline.py
    renderer.py
    run_generation.py
    scene.py
    configs/warehouse_blind_corner.yaml
  training/
    warehouse_dataset.py
    feature_extraction.py
    risk_labeling.py
    preprocess_real_dataset.py
    train_xgboost.py
    configs/real_data_training.yaml
packages/
  shared_schema/
  utils/
data/
  raw_real/
  raw_sim/
  processed/
  splits/
models/
outputs/
  previews/
  manifests/
  logs/
```

## Setup

```bash
cd /home/923873155/Hackathon_18Apr
python -m venv .venv
source .venv/bin/activate
pip install -r apps/training/requirements.txt
pip install -r apps/parser/requirements.txt
pip install -r apps/simulator/requirements.txt
pip install -r apps/inference/requirements.txt
pip install -r apps/backend/requirements.txt
pip install -e packages/simforge-sdk
```

## Real Dataset Layout

Place the extracted real dataset under:

```text
data/raw_real/lidar-warehouse-dataset/
  bin/
  label/
  vis/
  README.md
```

The public source describes the dataset as:

- consecutive VLP-16 LiDAR scans
- `.bin` point cloud files
- `.txt` 3D bounding box files
- labels for `FTS`, `ELFplusplus`, `CargoBike`, `Box`, and `ForkLift`
- no person annotations in the current release

## Run Order

### 1. Download the public warehouse LiDAR dataset

Use the source repo and dataset host referenced there:

- Repo: `https://github.com/anavsgmbh/lidar-warehouse-dataset`
- Dataset host: Google Drive link referenced in that repo README

After download/extract, make sure `data/raw_real/lidar-warehouse-dataset/bin` and `data/raw_real/lidar-warehouse-dataset/label` exist.

### 2. Build the real-data tabular dataset

```bash
python apps/training/preprocess_real_dataset.py \
  --dataset-root data/raw_real/lidar-warehouse-dataset \
  --dataset-name warehouse_lidar_real_features \
  --chunk-size 50
```

Outputs:

- `data/processed/warehouse_lidar_real_features/warehouse_lidar_real_features.csv`
- `data/processed/warehouse_lidar_real_features/warehouse_lidar_real_features.parquet`
- `data/processed/warehouse_lidar_real_features/feature_schema.json`
- `data/processed/warehouse_lidar_real_features/risk_label_derivation.json`
- `data/processed/warehouse_lidar_real_features/dataset_summary.json`
- `data/splits/warehouse_lidar_real_features/train.csv`
- `data/splits/warehouse_lidar_real_features/val.csv`
- `data/splits/warehouse_lidar_real_features/test.csv`

### 3. Train the binary risk model on GPU 0

```bash
python apps/training/train_xgboost.py \
  --dataset data/processed/warehouse_lidar_real_features/warehouse_lidar_real_features.parquet \
  --feature-schema data/processed/warehouse_lidar_real_features/feature_schema.json \
  --device cuda:0 \
  --task binary
```

### 4. Train the optional multiclass risk model on GPU 1

```bash
python apps/training/train_xgboost.py \
  --dataset data/processed/warehouse_lidar_real_features/warehouse_lidar_real_features.parquet \
  --feature-schema data/processed/warehouse_lidar_real_features/feature_schema.json \
  --device cuda:1 \
  --task multiclass
```

You can also pin the second GPU explicitly:

```bash
CUDA_VISIBLE_DEVICES=1 python apps/training/train_xgboost.py \
  --dataset data/processed/warehouse_lidar_real_features/warehouse_lidar_real_features.parquet \
  --feature-schema data/processed/warehouse_lidar_real_features/feature_schema.json \
  --device cuda:0 \
  --task binary
```

### 5. Parse user text into structured scenario JSON

Example via Python:

```python
from apps.parser import RuleBasedScenarioParser

parser = RuleBasedScenarioParser()
scenario = parser.parse("low light warehouse aisle with one blind corner and two pedestrians")
print(scenario.model_dump(mode="json"))
```

Example output:

```json
{
  "environment": "blind_corner_aisle",
  "lighting": "low",
  "blind_corner": true,
  "pedestrian_count": 2,
  "forklift_count": 0,
  "obstacle_density": "medium",
  "camera_view": "overhead",
  "difficulty": "hard",
  "reflective_floor": false,
  "robot_speed_mps": 1.35,
  "pedestrian_speed_mps": 1.15,
  "num_variants": 1,
  "dropped_object": false,
  "crossing_event": false,
  "description": "low light warehouse aisle with one blind corner and two pedestrians"
}
```

### 6. Generate preview scenarios locally without Isaac

```bash
python apps/simulator/run_generation.py \
  --description "narrow corridor with clutter and a forklift crossing ahead" \
  --job-id preview-local-001 \
  --num-variants 2
```

Outputs per generated variant:

- `data/raw_sim/<job_id>/<scenario_id>/scenario_manifest.json`
- `data/raw_sim/<job_id>/<scenario_id>/scenario_config.json`
- `data/raw_sim/<job_id>/<scenario_id>/generation_log.json`
- `data/raw_sim/<job_id>/<scenario_id>/scene.usda`
- `outputs/previews/<job_id>/<scenario_id>_preview.mp4`

### 7. Generate preview scenarios on the headless Isaac Sim cluster

Run from the Isaac Sim install root:

```bash
./python.sh /home/923873155/Hackathon_18Apr/apps/simulator/isaac_standalone.py \
  --description "high congestion loading zone with poor visibility" \
  --job-id preview-isaac-001
```

The standalone script launches `SimulationApp({"headless": True})`, opens the generated USDA stage, advances the simulation timeline, and writes an `isaac_capture.json` sidecar file.

### 8. Call the backend-friendly inference service

Python example:

```python
from apps.inference.service import WarehouseSafetyService

service = WarehouseSafetyService(model_dir="models/<trained-model-dir>")
result = service.process_description(
    description="low light warehouse aisle with one blind corner and two pedestrians",
    job_id="api-job-001",
    num_variants=1,
    use_isaac=False,
)
print(result.model_dump(mode="json"))
```

Returned fields include:

- `job_id`
- `status`
- `parsed_scenario`
- `generated_variants`
- `results[].risk_score`
- `results[].risk_label`
- `results[].explanation`
- `results[].preview_video_path`
- `results[].scenario_manifest_path`
- `results[].model_version`

## Real-Data Risk Target

The training pipeline derives targets from real LiDAR geometry and real 3D boxes:

- `unsafe_clearance_label`: triggered by low forward clearance, low nearest-object distance, or strong path blockage
- `congestion_risk_label`: triggered by congestion, low free-space ratio, or clutter
- `risk_label`: binary target used by the main model, set to `1` when the scene is at least caution-risk
- `risk_level`: optional multiclass target where `0=safe`, `1=caution`, `2=high`

Threshold definitions are saved to:

- `data/processed/<dataset_name>/risk_label_derivation.json`

Recommended operational interpretation for the binary model probability:

- `< 0.35`: safe
- `0.35 - 0.65`: caution
- `>= 0.65`: high risk

## Saved Model Artifacts

Each trained model directory contains:

- `risk_model.ubj`
- `model.pkl`
- `feature_schema.json`
- `metrics.json`
- `train_config.json`
- `feature_importance.json`

## Backend Integration Hooks

Backend-facing service modules:

- `apps/inference/service.py`
- `apps/backend/app/services/text_scenario_service.py`
- `apps/backend/app/services/pipeline_service.py`

Existing backend can either:

1. call `run_text_scenario_job(...)` with user text
2. or build a `ScenarioGenerationRequest` and call `WarehouseSafetyService.process_request(...)`

## Frontend Output Contract

The service layer returns everything the existing frontend needs to show:

- text input result
- processing state
- generated preview video
- risk score
- risk label
- short explanation
- manifest download path

## Assumptions

- The public warehouse dataset is placed under `data/raw_real/lidar-warehouse-dataset`.
- Point cloud `.bin` files are float32 and are either XYZ or XYZI; the loader infers 3 or 4 channels.
- The current public dataset release has no person labels, so `object_count_human` remains zero in real-data training.
- Isaac Sim is installed on the target GPU cluster and launched with its bundled `python.sh`.

## Known Risks

- Human-related risk behavior in the trained model is limited because the public real dataset currently lacks person annotations.
- The risk targets are heuristic labels derived from real geometry, not manually curated incident outcomes.
- Isaac-native RTX LiDAR and camera capture usually need version-specific API wiring; the provided standalone script is structured for that path but may need small adjustments for the exact Isaac version deployed on the cluster.
- GPU XGBoost requires a GPU-enabled build of `xgboost`; verify this on the cluster before long runs.

## Next Steps

1. Add a small regression test suite for parser output and feature-schema compatibility.
2. Swap the simple preview renderer for fuller Isaac-native camera capture once the cluster Isaac version is fixed.
3. Add calibration plots and threshold tuning once you inspect class balance on the real dataset.
4. If you later acquire person-labeled warehouse LiDAR data, retrain the model with real pedestrian features instead of zero-filled placeholders.
