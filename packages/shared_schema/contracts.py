"""Shared schemas for real-data training, text parsing, simulation, and inference."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


FEATURE_SCHEMA_VERSION = "2026-04-18-real-risk-v2"
PIPELINE_SCHEMA_VERSION = "2026-04-18-sim-service-v2"


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    CRITICAL = "critical"


class CameraView(str, Enum):
    OVERHEAD = "overhead"
    FOLLOW = "follow"
    FIXED_ANGLE = "fixed_angle"
    FIRST_PERSON = "first_person"
    MULTI_VIEW = "multi_view"


class LightingLevel(str, Enum):
    BRIGHT = "bright"
    NORMAL = "normal"
    LOW = "low"
    POOR = "poor"
    EMERGENCY = "emergency"


class EnvironmentType(str, Enum):
    WAREHOUSE_AISLE = "warehouse_aisle"
    NARROW_CORRIDOR = "narrow_corridor"
    LOADING_ZONE = "loading_zone"
    BLIND_CORNER_AISLE = "blind_corner_aisle"


class ObstacleDensityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskLabel(str, Enum):
    SAFE = "safe"
    CAUTION = "caution"
    HIGH = "high"


class ParsedScenario(BaseModel):
    """Validated user-facing scenario JSON produced by the parser."""

    environment: EnvironmentType = EnvironmentType.WAREHOUSE_AISLE
    lighting: LightingLevel = LightingLevel.NORMAL
    blind_corner: bool = False
    pedestrian_count: int = Field(default=0, ge=0, le=10)
    forklift_count: int = Field(default=0, ge=0, le=5)
    obstacle_density: ObstacleDensityLevel = ObstacleDensityLevel.MEDIUM
    camera_view: CameraView = CameraView.OVERHEAD
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    reflective_floor: bool = False
    robot_speed_mps: float = Field(default=1.2, gt=0.1, le=4.0)
    pedestrian_speed_mps: float = Field(default=1.0, ge=0.0, le=3.0)
    num_variants: int = Field(default=1, ge=1, le=32)
    dropped_object: bool = False
    crossing_event: bool = False
    description: str = ""

    @model_validator(mode="after")
    def validate_combinations(self) -> "ParsedScenario":
        if self.blind_corner and self.environment == EnvironmentType.LOADING_ZONE:
            raise ValueError("blind_corner is not supported with loading_zone in this version")
        if self.crossing_event and self.pedestrian_count == 0 and self.forklift_count == 0:
            raise ValueError("crossing_event requires at least one pedestrian or forklift")
        return self


class ScenarioGenerationRequest(BaseModel):
    """Internal simulation request used by the simulator and backend."""

    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario_type: str = "warehouse_safety"
    environment_preset: str = EnvironmentType.WAREHOUSE_AISLE.value
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    lighting_level: LightingLevel = LightingLevel.NORMAL
    reflective_floor: bool = False
    human_count: int = Field(default=0, ge=0, le=10)
    obstacle_count: int = Field(default=2, ge=0, le=50)
    forklift_count: int = Field(default=0, ge=0, le=5)
    robot_speed_mps: float = Field(default=1.2, gt=0.1, le=4.0)
    human_speed_mps: float = Field(default=1.0, ge=0.0, le=3.0)
    blind_corner: bool = False
    dropped_object: bool = False
    crossing_event: bool = False
    camera_view: CameraView = CameraView.OVERHEAD
    num_variants: int = Field(default=1, ge=1, le=128)
    base_seed: int = 42
    headless: bool = True
    use_isaac: bool = False
    output_root: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    description: str = ""

    @classmethod
    def from_parsed_scenario(
        cls,
        parsed: ParsedScenario,
        job_id: str | None = None,
        use_isaac: bool = False,
        headless: bool = True,
        base_seed: int = 42,
        metadata: dict[str, Any] | None = None,
    ) -> "ScenarioGenerationRequest":
        obstacle_count_map = {
            ObstacleDensityLevel.LOW: 1,
            ObstacleDensityLevel.MEDIUM: 3,
            ObstacleDensityLevel.HIGH: 5,
        }
        return cls(
            job_id=job_id or str(uuid.uuid4()),
            scenario_type=parsed.environment.value,
            environment_preset=parsed.environment.value,
            difficulty=parsed.difficulty,
            lighting_level=parsed.lighting,
            reflective_floor=parsed.reflective_floor,
            human_count=parsed.pedestrian_count,
            obstacle_count=obstacle_count_map[parsed.obstacle_density],
            forklift_count=parsed.forklift_count,
            robot_speed_mps=parsed.robot_speed_mps,
            human_speed_mps=parsed.pedestrian_speed_mps,
            blind_corner=parsed.blind_corner,
            dropped_object=parsed.dropped_object,
            crossing_event=parsed.crossing_event,
            camera_view=parsed.camera_view,
            num_variants=parsed.num_variants,
            base_seed=base_seed,
            headless=headless,
            use_isaac=use_isaac,
            metadata=metadata or {},
            description=parsed.description,
        )


class ScenarioVariantConfig(BaseModel):
    """Resolved variant-specific scenario configuration."""

    job_id: str
    scenario_id: str
    scenario_seed: int
    scene_family: str
    variant_index: int
    scenario_type: str
    environment_preset: str
    difficulty: DifficultyLevel
    lighting_level: LightingLevel
    reflective_floor: bool
    human_count: int
    obstacle_count: int
    forklift_count: int
    robot_speed_mps: float
    human_speed_mps: float
    blind_corner: bool
    dropped_object: bool
    crossing_event: bool
    camera_view: CameraView
    headless: bool = True
    use_isaac: bool = False
    description: str = ""


class ScenarioManifest(BaseModel):
    """Manifest for one generated preview scenario."""

    schema_version: str = PIPELINE_SCHEMA_VERSION
    job_id: str
    scenario_id: str
    scenario_seed: int
    scene_family: str
    variant_index: int
    scenario_type: str
    environment_preset: str
    difficulty: DifficultyLevel
    camera_view: CameraView
    lighting_level: LightingLevel
    use_isaac: bool
    headless: bool
    parsed_scenario: dict[str, Any] = Field(default_factory=dict)
    variant_parameters: dict[str, Any] = Field(default_factory=dict)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ScenarioMetadata(BaseModel):
    """Generation log / metadata for traceability."""

    schema_version: str = PIPELINE_SCHEMA_VERSION
    job_id: str
    scenario_id: str
    variant_index: int
    scenario_seed: int
    scene_family: str
    generator: str
    status: str
    output_dir: str
    preview_asset_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    retries: int = 0
    notes: list[str] = Field(default_factory=list)
    runtime: dict[str, Any] = Field(default_factory=dict)


class WarehouseRiskFeatureRow(BaseModel):
    """Structured tabular feature row used for model training and inference."""

    scan_id: str
    frame_index: int = Field(ge=0)
    sequence_id: str
    scan_chunk: str
    environment_type: str = EnvironmentType.WAREHOUSE_AISLE.value
    object_count_total: int = Field(ge=0)
    object_count_human: int = Field(ge=0)
    object_count_forklift: int = Field(ge=0)
    object_count_pallet: int = Field(ge=0)
    object_count_vehicle_platform: int = Field(ge=0)
    nearest_object_distance_m: float = Field(ge=0.0)
    nearest_human_distance_m: float = Field(ge=0.0)
    average_obstacle_distance_m: float = Field(ge=0.0)
    obstacle_density: float = Field(ge=0.0)
    left_clearance_m: float = Field(ge=0.0)
    right_clearance_m: float = Field(ge=0.0)
    front_clearance_m: float = Field(ge=0.0)
    free_space_ratio: float = Field(ge=0.0, le=1.0)
    clutter_score: float = Field(ge=0.0, le=1.0)
    occlusion_proxy: float = Field(ge=0.0, le=1.0)
    bbox_volume_mean: float = Field(ge=0.0)
    bbox_volume_max: float = Field(ge=0.0)
    object_speed_proxy: float = Field(ge=0.0)
    path_blockage_score: float = Field(ge=0.0, le=1.0)
    congestion_score: float = Field(ge=0.0, le=1.0)
    unsafe_clearance_label: int = Field(default=0, ge=0, le=1)
    congestion_risk_label: int = Field(default=0, ge=0, le=1)
    obstacle_proximity_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_label: int = Field(default=0, ge=0, le=1)
    risk_level: int = Field(default=0, ge=0, le=2)


class FeatureSchema(BaseModel):
    """Versioned model feature contract."""

    version: str
    numeric_features: list[str]
    categorical_features: list[str]
    categorical_levels: dict[str, list[str]]
    encoded_columns: list[str]
    target_columns: list[str]
    group_columns: list[str]
    defaults: dict[str, Any]
    ranges: dict[str, tuple[float | int, float | int]]
    dropped_columns: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GeneratedVariantArtifact(BaseModel):
    """Paths produced by the simulation pipeline for one variant."""

    job_id: str
    scenario_id: str
    variant_index: int
    status: str
    manifest_path: str
    scenario_config_path: str
    generation_log_path: str
    preview_video_path: str
    scene_usd_path: str
    model_features_path: str | None = None
    # Compatibility with the earlier backend integration prototype.
    labels_path: str | None = None
    lidar_features_path: str | None = None
    metadata_path: str | None = None
    annotations_path: str | None = None


class InferenceResponse(BaseModel):
    """Backend-facing payload for one generated scenario variant."""

    job_id: str
    scenario_id: str
    variant_index: int
    status: str
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_label: RiskLabel
    explanation: str
    preview_video_path: str
    scenario_manifest_path: str
    model_version: str
    feature_schema_version: str
    supporting_signals: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class PipelineJobResponse(BaseModel):
    """Full service response returned to the backend."""

    job_id: str
    status: str
    parsed_scenario: dict[str, Any] = Field(default_factory=dict)
    generated_variants: list[GeneratedVariantArtifact] = Field(default_factory=list)
    results: list[InferenceResponse] = Field(default_factory=list)
    model_version: str | None = None
    feature_schema_version: str | None = None
