"""SQLAlchemy database models for SimForge."""

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import declarative_base, relationship

from app.core.time import utc_now

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, default="developer")
    created_at = Column(DateTime(timezone=True), default=utc_now)


class Scenario(Base):
    __tablename__ = "scenarios"
    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    environment_template = Column(String, default="warehouse_aisle")
    robot_path_type = Column(String, default="left_turn_blind_corner")
    human_crossing_probability = Column(Float, default=0.5)
    dropped_obstacle_level = Column(String, default="medium")
    blocked_aisle_enabled = Column(Boolean, default=False)
    lighting_preset = Column(String, default="normal")
    camera_mode = Column(String, default="overhead")
    variant_count = Column(Integer, default=5)
    random_seed = Column(Integer, default=42)
    notes = Column(Text, default="")
    status = Column(String, default="draft")
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    variants = relationship("ScenarioVariant", back_populates="scenario", cascade="all, delete-orphan")
    jobs = relationship("SimulationJob", back_populates="scenario", cascade="all, delete-orphan")


class ScenarioVariant(Base):
    __tablename__ = "scenario_variants"
    id = Column(String, primary_key=True, default=gen_uuid)
    scenario_id = Column(String, ForeignKey("scenarios.id"), nullable=False)
    variant_index = Column(Integer, nullable=False)
    variant_parameters_json = Column(JSON, default=dict)
    deterministic_seed = Column(Integer, nullable=False)
    status = Column(String, default="queued")
    created_at = Column(DateTime(timezone=True), default=utc_now)

    scenario = relationship("Scenario", back_populates="variants")


class SimulationJob(Base):
    __tablename__ = "simulation_jobs"
    id = Column(String, primary_key=True, default=gen_uuid)
    scenario_id = Column(String, ForeignKey("scenarios.id"), nullable=False)
    variant_id = Column(String, ForeignKey("scenario_variants.id"), nullable=True)
    provider_type = Column(String, default="mock")
    mode = Column(String, default="mock")
    status = Column(String, default="queued")
    submitted_at = Column(DateTime(timezone=True), default=utc_now)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    log_path = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)

    scenario = relationship("Scenario", back_populates="jobs")
    artifacts = relationship("OutputArtifact", back_populates="job", cascade="all, delete-orphan")
    evaluation = relationship("EvaluationReport", back_populates="job", uselist=False, cascade="all, delete-orphan")


class OutputArtifact(Base):
    __tablename__ = "output_artifacts"
    id = Column(String, primary_key=True, default=gen_uuid)
    job_id = Column(String, ForeignKey("simulation_jobs.id"), nullable=False)
    artifact_type = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    preview_path = Column(String, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    job = relationship("SimulationJob", back_populates="artifacts")


class EvaluationReport(Base):
    __tablename__ = "evaluation_reports"
    id = Column(String, primary_key=True, default=gen_uuid)
    job_id = Column(String, ForeignKey("simulation_jobs.id"), nullable=False, unique=True)
    collision_risk_score = Column(Float, default=0.0)
    occlusion_score = Column(Float, default=0.0)
    path_conflict_score = Column(Float, default=0.0)
    severity_score = Column(Float, default=0.0)
    diversity_score = Column(Float, default=0.0)
    coverage_summary_json = Column(JSON, default=dict)
    explanation = Column(Text, default="")
    top_risk_factors = Column(JSON, default=list)
    recommended_actions = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    job = relationship("SimulationJob", back_populates="evaluation")


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(String, primary_key=True, default=gen_uuid)
    event_type = Column(String, nullable=False)
    related_entity_type = Column(String, nullable=True)
    related_entity_id = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class SystemSetting(Base):
    __tablename__ = "system_settings"
    id = Column(String, primary_key=True, default=gen_uuid)
    key = Column(String, unique=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
