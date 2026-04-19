"""Mock Simulation Provider — generates realistic placeholder outputs for development and demo."""

import json
import os
import random
import uuid
from datetime import UTC, datetime
from typing import Any

from apps.runner.providers import SimulationProvider


def utc_now_iso() -> str:
    """Return an ISO8601 UTC timestamp."""
    return datetime.now(UTC).isoformat()


class MockSimulationProvider(SimulationProvider):
    """Mock simulation provider for local development and demo.

    Generates realistic placeholder outputs including:
    - Preview images (placeholder PNGs)
    - Manifest JSON
    - Labels JSON
    - Evaluation JSON
    - Log files

    No GPU or Isaac Sim required.
    """

    def __init__(self, storage_root: str = "./storage"):
        self.storage_root = storage_root
        os.makedirs(f"{storage_root}/artifacts", exist_ok=True)
        os.makedirs(f"{storage_root}/previews", exist_ok=True)
        os.makedirs(f"{storage_root}/logs", exist_ok=True)

    async def prepare_run(self, job_id: str, variant_params: dict[str, Any]) -> dict:
        """Prepare mock run — validates params and creates working directory."""
        work_dir = f"{self.storage_root}/jobs/{job_id}"
        os.makedirs(work_dir, exist_ok=True)
        return {
            "job_id": job_id,
            "work_dir": work_dir,
            "variant_params": variant_params,
            "prepared_at": utc_now_iso(),
        }

    async def submit_run(self, job_id: str, preparation: dict) -> dict:
        """Submit mock run — generates all placeholder outputs."""
        rng = random.Random(hash(job_id))
        work_dir = preparation["work_dir"]
        params = preparation.get("variant_params", {})

        # Generate manifest
        manifest = {
            "job_id": job_id,
            "provider": "mock",
            "environment": params.get("environment_template", "warehouse_aisle"),
            "robot_path": params.get("robot_path_type", "left_turn_blind_corner"),
            "variant_index": params.get("variant_index", 0),
            "frame_count": rng.randint(120, 360),
            "resolution": [1920, 1080],
            "fps": 30,
            "render_engine": "mock_renderer",
            "timestamp": utc_now_iso(),
        }
        with open(f"{work_dir}/manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # Generate labels
        labels = {
            "job_id": job_id,
            "objects": [
                {"type": "amr", "id": "robot_01", "frames_visible": manifest["frame_count"]},
                {"type": "human", "id": "human_01", "frames_visible": int(manifest["frame_count"] * 0.6) if params.get("human_present") else 0},
            ] + [
                {"type": "obstacle", "id": f"box_{i}", "frames_visible": manifest["frame_count"]}
                for i in range(params.get("obstacle_count", 1))
            ],
            "events": [
                {"frame": rng.randint(30, 150), "type": "near_miss", "severity": params.get("hazard_severity", "medium")},
                {"frame": rng.randint(60, 200), "type": "path_deviation", "magnitude": round(rng.uniform(0.1, 0.8), 2)},
            ],
        }
        with open(f"{work_dir}/labels.json", "w") as f:
            json.dump(labels, f, indent=2)

        # Generate log
        log_lines = [
            f"[{utc_now_iso()}] MockSimulation started for job {job_id}",
            f"[{utc_now_iso()}] Loading environment: {params.get('environment_template', 'warehouse_aisle')}",
            f"[{utc_now_iso()}] Spawning actors: AMR, Human (present={params.get('human_present', False)})",
            f"[{utc_now_iso()}] Rendering {manifest['frame_count']} frames at {manifest['fps']}fps",
            f"[{utc_now_iso()}] Simulation completed successfully",
        ]
        with open(f"{work_dir}/simulation.log", "w") as f:
            f.write("\n".join(log_lines))

        return {"job_id": job_id, "status": "completed", "output_dir": work_dir}

    async def get_status(self, job_id: str) -> str:
        return "completed"

    async def collect_outputs(self, job_id: str) -> list[dict]:
        work_dir = f"{self.storage_root}/jobs/{job_id}"
        outputs = []
        for fname in os.listdir(work_dir) if os.path.exists(work_dir) else []:
            outputs.append({
                "file_path": f"{work_dir}/{fname}",
                "artifact_type": self._classify_artifact(fname),
            })
        return outputs

    async def cleanup(self, job_id: str) -> None:
        pass  # Keep outputs for demo

    def _classify_artifact(self, filename: str) -> str:
        if "manifest" in filename:
            return "manifest_json"
        elif "labels" in filename:
            return "labels_json"
        elif "eval" in filename:
            return "evaluation_json"
        elif filename.endswith(".log"):
            return "log_file"
        elif filename.endswith((".png", ".jpg")):
            return "preview_image"
        return "log_file"
