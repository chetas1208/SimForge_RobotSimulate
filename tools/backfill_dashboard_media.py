#!/usr/bin/env python3
"""Backfill dashboard-friendly media and prompt artifacts for completed jobs."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, joinedload, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "backend"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.models import OutputArtifact, Scenario, SimulationJob  # noqa: E402
from app.core.time import utc_now  # noqa: E402
from apps.runner.preview_services.seedance.service import SeedancePreviewService  # noqa: E402
from pxr import Usd  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db-url",
        default=f"sqlite:///{BACKEND_ROOT / 'simforge_local.db'}",
        help="SQLAlchemy database URL for the live backend database.",
    )
    parser.add_argument(
        "--scenario-id",
        default="",
        help="Optional scenario ID to limit processing.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional maximum number of jobs to process.",
    )
    parser.add_argument(
        "--skip-seedance",
        action="store_true",
        help="Skip the outbound Seedance generation attempt and only backfill USD/NIM artifacts.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def build_text_stage_summary(scene_path: Path) -> dict:
    scene_text = scene_path.read_text(encoding="utf-8")

    def capture(pattern: str, cast=str):
        match = re.search(pattern, scene_text)
        if not match:
            return None
        return cast(match.group(1))

    prim_paths = re.findall(r'def\s+\w+\s+"([^"]+)"', scene_text)
    return {
        "default_prim": capture(r'defaultPrim\s*=\s*"([^"]+)"'),
        "prim_count": len(prim_paths),
        "prim_paths": prim_paths,
        "environment_preset": capture(r'custom string preset = "([^"]+)"'),
        "lighting": capture(r'custom string lighting = "([^"]+)"'),
        "pedestrian_count": capture(r'custom int count = (\d+)', int),
        "forklift_count": capture(r'def Xform "Forklifts"\s*{\s*custom int count = (\d+)', int),
        "camera_paths": re.findall(r'def Xform "([^"]+)" \{ custom string purpose = "preview"', scene_text),
        "parser": "regex_fallback",
    }


def build_stage_summary(scene_path: Path) -> dict:
    try:
        stage = Usd.Stage.Open(str(scene_path))
    except Exception:
        return build_text_stage_summary(scene_path)
    if stage is None:
        return build_text_stage_summary(scene_path)

    world = stage.GetDefaultPrim()
    env = stage.GetPrimAtPath("/World/WarehouseEnvironment")
    pedestrians = stage.GetPrimAtPath("/World/Pedestrians")
    forklifts = stage.GetPrimAtPath("/World/Forklifts")
    sensors = stage.GetPrimAtPath("/World/Sensors")

    prim_paths = [str(prim.GetPath()) for prim in stage.Traverse()]
    camera_paths = [str(child.GetPath()) for child in sensors.GetChildren()] if sensors.IsValid() else []

    return {
        "default_prim": world.GetName() if world and world.IsValid() else None,
        "prim_count": len(prim_paths),
        "prim_paths": prim_paths,
        "environment_preset": env.GetAttribute("preset").Get() if env.IsValid() else None,
        "lighting": env.GetAttribute("lighting").Get() if env.IsValid() else None,
        "pedestrian_count": pedestrians.GetAttribute("count").Get() if pedestrians.IsValid() else None,
        "forklift_count": forklifts.GetAttribute("count").Get() if forklifts.IsValid() else None,
        "camera_paths": camera_paths,
        "parser": "pxr_usd",
    }


def convert_preview_to_mp4(preview_path: Path) -> Path:
    if preview_path.suffix.lower() == ".mp4":
        return preview_path

    import imageio.v2 as imageio

    frames = imageio.mimread(preview_path)
    mp4_path = preview_path.with_suffix(".mp4")
    imageio.mimwrite(mp4_path, frames, fps=12)
    return mp4_path


def upsert_artifact(
    db: Session,
    job: SimulationJob,
    artifact_type: str,
    file_path: str,
    metadata: dict,
    preview_path: str | None = None,
) -> OutputArtifact:
    for artifact in job.artifacts:
        if artifact.artifact_type != artifact_type:
            continue
        current_role = (artifact.metadata_json or {}).get("video_role")
        desired_role = metadata.get("video_role")
        if current_role == desired_role:
            artifact.file_path = file_path
            artifact.preview_path = preview_path
            artifact.metadata_json = metadata
            return artifact
        if artifact_type == "preview_video" and desired_role == "simulated" and current_role in {None, "", "simulated"}:
            artifact.file_path = file_path
            artifact.preview_path = preview_path
            artifact.metadata_json = metadata
            return artifact
        if artifact_type == "prompt_json" and current_role in {None, "", "prompt_package"}:
            artifact.file_path = file_path
            artifact.preview_path = preview_path
            artifact.metadata_json = metadata
            return artifact

    artifact = OutputArtifact(
        id=str(uuid.uuid4()),
        job_id=job.id,
        artifact_type=artifact_type,
        file_path=file_path,
        preview_path=preview_path,
        metadata_json=metadata,
        created_at=utc_now(),
    )
    db.add(artifact)
    job.artifacts.append(artifact)
    return artifact


def select_jobs(db: Session, scenario_id: str, limit: int) -> list[SimulationJob]:
    query = (
        db.query(SimulationJob)
        .options(joinedload(SimulationJob.artifacts), joinedload(SimulationJob.scenario))
        .join(Scenario, Scenario.id == SimulationJob.scenario_id)
        .filter(SimulationJob.status == "completed")
        .order_by(Scenario.updated_at.desc(), SimulationJob.completed_at.desc())
    )
    if scenario_id:
        query = query.filter(SimulationJob.scenario_id == scenario_id)
    jobs = list(query.all())
    if limit > 0:
        jobs = jobs[:limit]
    return jobs


def main() -> int:
    args = parse_args()

    env_path = BACKEND_ROOT / ".env"
    if env_path.exists():
        from dotenv import load_dotenv

        load_dotenv(env_path)

    engine = create_engine(args.db_url, future=True)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    preview_service = SeedancePreviewService()

    processed = 0
    generated = 0
    failed_seedance = 0

    with session() as db:
        jobs = select_jobs(db, args.scenario_id, args.limit)
        print(f"Processing {len(jobs)} completed jobs")

        for job in jobs:
            artifacts_by_type: dict[str, list[OutputArtifact]] = {}
            for artifact in job.artifacts:
                artifacts_by_type.setdefault(artifact.artifact_type, []).append(artifact)

            usd_artifacts = artifacts_by_type.get("usd_scene", [])
            preview_artifacts = artifacts_by_type.get("preview_video", [])
            manifest_artifacts = artifacts_by_type.get("manifest_json", [])
            config_artifacts = artifacts_by_type.get("config_json", [])

            if not usd_artifacts or not preview_artifacts or not manifest_artifacts or not config_artifacts:
                print(f"Skipping {job.id}: missing USD/config/manifest/preview artifacts")
                continue

            usd_path = Path(usd_artifacts[0].file_path)
            simulation_artifact = next(
                (artifact for artifact in preview_artifacts if (artifact.metadata_json or {}).get("video_role") != "generated_concept"),
                preview_artifacts[0],
            )
            preview_path = Path(simulation_artifact.file_path)
            manifest_path = Path(manifest_artifacts[0].file_path)
            config_path = Path(config_artifacts[0].file_path)

            if not usd_path.exists() or not preview_path.exists():
                print(f"Skipping {job.id}: missing files on disk")
                continue

            stage_summary = build_stage_summary(usd_path)
            scene_usda = usd_path.read_text(encoding="utf-8")
            manifest = load_json(manifest_path)
            scenario_config = load_json(config_path)

            normalized_preview_path = convert_preview_to_mp4(preview_path)
            simulation_metadata = dict(simulation_artifact.metadata_json or {})
            simulation_metadata.update({
                "provider": simulation_metadata.get("provider", job.mode),
                "video_role": "simulated",
                "label": "Simulated Scenario Video",
                "stage_summary": stage_summary,
            })
            simulation_artifact.file_path = str(normalized_preview_path)
            simulation_artifact.preview_path = str(normalized_preview_path)
            simulation_artifact.metadata_json = simulation_metadata

            scene_description = preview_service._describe_scene(
                scenario_config=scenario_config,
                manifest=manifest,
                scene_usda=scene_usda,
            )
            base_prompt = preview_service._create_video_prompt(scene_description)
            refined_prompt = preview_service._enhance_with_llm(base_prompt)

            prompt_payload = {
                "job_id": job.id,
                "scenario_id": job.scenario_id,
                "scene_usd_path": str(usd_path),
                "stage_summary": stage_summary,
                "scene_description": scene_description,
                "base_prompt": base_prompt,
                "refined_prompt": refined_prompt,
                "seedance_request": {
                    "prompt": refined_prompt,
                    "duration": 10,
                    "resolution": "720p",
                    "style": "cinematic",
                    "fps": 24,
                },
            }

            concept_path = normalized_preview_path.with_name(normalized_preview_path.stem.replace("_preview", "_seedance_concept") + ".mp4")
            if args.skip_seedance:
                prompt_payload["seedance_status"] = "skipped"
            else:
                try:
                    video_url = preview_service._generate_seedance(refined_prompt)
                    downloaded_path = preview_service._download_video(video_url, concept_path)
                    prompt_payload["seedance_status"] = "completed"
                    prompt_payload["seedance_video_url"] = video_url
                    upsert_artifact(
                        db=db,
                        job=job,
                        artifact_type="preview_video",
                        file_path=str(downloaded_path),
                        preview_path=str(downloaded_path),
                        metadata={
                            "provider": "seedance",
                            "video_role": "generated_concept",
                            "label": "Seedance Concept Video",
                            "prompt_source": "prompt_json",
                        },
                    )
                    generated += 1
                except Exception as exc:
                    prompt_payload["seedance_status"] = "failed"
                    prompt_payload["seedance_error"] = str(exc)
                    failed_seedance += 1

            prompt_path = usd_path.with_name("seedance_prompt.json")
            dump_json(prompt_path, prompt_payload)
            upsert_artifact(
                db=db,
                job=job,
                artifact_type="prompt_json",
                file_path=str(prompt_path),
                preview_path=None,
                metadata={
                    "provider": "nvidia_nim",
                    "video_role": "prompt_package",
                    "label": "Seedance Prompt Package",
                    "seedance_status": prompt_payload.get("seedance_status"),
                    "seedance_error": prompt_payload.get("seedance_error"),
                    "scene_description_excerpt": scene_description[:220],
                    "refined_prompt_excerpt": refined_prompt[:220],
                },
            )

            processed += 1
            print(f"Processed job {job.id} | simulated={normalized_preview_path.name} | seedance={prompt_payload['seedance_status']}")

        db.commit()

    print(f"Done | processed={processed} | generated={generated} | failed_seedance={failed_seedance}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
