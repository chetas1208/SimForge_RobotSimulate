"""Core types and models for the SimForge SDK."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    QUEUED = "queued"
    PREPARING = "preparing"
    RUNNING = "running"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class ProviderType(str, Enum):
    MOCK = "mock"
    ISAAC = "isaac"
    TRACK4 = "track4"


class LightingPreset(str, Enum):
    NORMAL = "normal"
    LOW_LIGHT = "low_light"
    HIGH_CONTRAST = "high_contrast"
    FLICKERING = "flickering"
    EMERGENCY = "emergency"


class CameraMode(str, Enum):
    OVERHEAD = "overhead"
    FOLLOW = "follow"
    FIXED_ANGLE = "fixed_angle"
    FIRST_PERSON = "first_person"
    MULTI_VIEW = "multi_view"


class ObstacleLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class RobotPathType(str, Enum):
    LEFT_TURN_BLIND_CORNER = "left_turn_blind_corner"
    RIGHT_TURN_BLIND_CORNER = "right_turn_blind_corner"
    STRAIGHT_AISLE = "straight_aisle"
    T_JUNCTION = "t_junction"
    CROSS_INTERSECTION = "cross_intersection"
    U_TURN = "u_turn"


class EnvironmentTemplate(str, Enum):
    WAREHOUSE_AISLE = "warehouse_aisle"
    WAREHOUSE_OPEN_FLOOR = "warehouse_open_floor"
    WAREHOUSE_LOADING_DOCK = "warehouse_loading_dock"
    WAREHOUSE_COLD_STORAGE = "warehouse_cold_storage"


class ArtifactType(str, Enum):
    PREVIEW_VIDEO = "preview_video"
    PREVIEW_IMAGE = "preview_image"
    MANIFEST_JSON = "manifest_json"
    CONFIG_JSON = "config_json"
    FEATURE_JSON = "feature_json"
    LABELS_JSON = "labels_json"
    EVALUATION_JSON = "evaluation_json"
    LOG_FILE = "log_file"
    USD_SCENE = "usd_scene"
    PROMPT_JSON = "prompt_json"


class ScenarioStatus(str, Enum):
    DRAFT = "draft"
    COMPILED = "compiled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Models ───────────────────────────────────────────────────────────────────

def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)

class Scenario(BaseModel):
    """A structured warehouse edge-case scenario definition."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    environment_template: EnvironmentTemplate = EnvironmentTemplate.WAREHOUSE_AISLE
    robot_path_type: RobotPathType = RobotPathType.LEFT_TURN_BLIND_CORNER
    human_crossing_probability: float = Field(default=0.5, ge=0.0, le=1.0)
    dropped_obstacle_level: ObstacleLevel = ObstacleLevel.MEDIUM
    blocked_aisle_enabled: bool = False
    lighting_preset: LightingPreset = LightingPreset.NORMAL
    camera_mode: CameraMode = CameraMode.OVERHEAD
    variant_count: int = Field(default=5, ge=1, le=100)
    random_seed: int = Field(default=42)
    notes: str = Field(default="")
    status: ScenarioStatus = ScenarioStatus.DRAFT
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    model_config = {"use_enum_values": True}


class ScenarioVariant(BaseModel):
    """A deterministically generated variant of a scenario."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario_id: str
    variant_index: int
    variant_parameters: dict[str, Any] = Field(default_factory=dict)
    deterministic_seed: int
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {"use_enum_values": True}


class SimulationRun(BaseModel):
    """A simulation job execution record."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario_id: str
    variant_id: Optional[str] = None
    provider_type: ProviderType = ProviderType.MOCK
    mode: str = "mock"
    status: JobStatus = JobStatus.QUEUED
    submitted_at: datetime = Field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    log_path: Optional[str] = None
    error_message: Optional[str] = None

    model_config = {"use_enum_values": True}


class Artifact(BaseModel):
    """An output artifact from a simulation run."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    artifact_type: ArtifactType
    file_path: str
    preview_path: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {"use_enum_values": True}


class EvaluationReport(BaseModel):
    """Evaluation results for a simulation run."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    collision_risk_score: float = Field(ge=0.0, le=1.0)
    occlusion_score: float = Field(ge=0.0, le=1.0)
    path_conflict_score: float = Field(ge=0.0, le=1.0)
    severity_score: float = Field(ge=0.0, le=1.0)
    diversity_score: float = Field(ge=0.0, le=1.0)
    coverage_summary: dict[str, Any] = Field(default_factory=dict)
    explanation: str = ""
    top_risk_factors: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class SubmitRunResponse(BaseModel):
    """Response from submitting a scenario run."""

    run_id: str
    scenario_id: str
    job_ids: list[str] = Field(default_factory=list)
    variant_count: int
    status: str = "queued"
    message: str = ""
