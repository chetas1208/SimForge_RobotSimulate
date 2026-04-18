"""Filesystem helpers for project-relative data, model, and output paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW_REAL = PROJECT_ROOT / "data" / "raw_real"
DATA_RAW_SIM = PROJECT_ROOT / "data" / "raw_sim"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_SPLITS = PROJECT_ROOT / "data" / "splits"
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUT_PREVIEWS = PROJECT_ROOT / "outputs" / "previews"
OUTPUT_MANIFESTS = PROJECT_ROOT / "outputs" / "manifests"
OUTPUT_LOGS = PROJECT_ROOT / "outputs" / "logs"


@dataclass(frozen=True)
class ScenarioPaths:
    root_dir: Path
    preview_dir: Path
    manifest_dir: Path
    log_dir: Path
    scene_dir: Path


def ensure_project_dirs() -> None:
    for path in (
        DATA_RAW_REAL,
        DATA_RAW_SIM,
        DATA_PROCESSED,
        DATA_SPLITS,
        MODELS_DIR,
        OUTPUT_PREVIEWS,
        OUTPUT_MANIFESTS,
        OUTPUT_LOGS,
    ):
        path.mkdir(parents=True, exist_ok=True)


def build_scenario_paths(job_id: str, scenario_id: str) -> ScenarioPaths:
    ensure_project_dirs()
    root_dir = DATA_RAW_SIM / job_id / scenario_id
    preview_dir = OUTPUT_PREVIEWS / job_id
    manifest_dir = OUTPUT_MANIFESTS / job_id
    log_dir = OUTPUT_LOGS / job_id
    scene_dir = root_dir
    for path in (root_dir, preview_dir, manifest_dir, log_dir):
        path.mkdir(parents=True, exist_ok=True)
    return ScenarioPaths(
        root_dir=root_dir,
        preview_dir=preview_dir,
        manifest_dir=manifest_dir,
        log_dir=log_dir,
        scene_dir=scene_dir,
    )


def resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path
