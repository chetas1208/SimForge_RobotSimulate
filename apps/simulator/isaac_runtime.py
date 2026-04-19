"""Helpers to execute scenario generation inside Isaac Sim's bundled Python."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from packages.shared_schema import GeneratedVariantArtifact, ScenarioGenerationRequest
from packages.utils import OUTPUT_LOGS, PROJECT_ROOT, read_json, write_json


def _resolve_isaac_python() -> str:
    explicit = os.getenv("ISAAC_PYTHON", "").strip()
    if explicit:
        return explicit

    sim_path = os.getenv("ISAAC_SIM_PATH", "").strip()
    if sim_path:
        return str(Path(sim_path) / "python.sh")

    raise RuntimeError(
        "Isaac runtime requested but ISAAC_PYTHON or ISAAC_SIM_PATH is not configured."
    )


def _build_isaac_env(isaac_python: str) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("OMNI_KIT_ACCEPT_EULA", "YES")

    python_path = Path(isaac_python).resolve()
    if python_path.parent.name == "bin":
        inferred_lib_dir = python_path.parent.parent / "lib"
    else:
        inferred_lib_dir = python_path.parent / "lib"

    preferred_lib_dir = os.getenv("ISAAC_LD_LIBRARY_PATH", "").strip()
    lib_dir = Path(preferred_lib_dir) if preferred_lib_dir else inferred_lib_dir
    if lib_dir.exists():
        existing = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = f"{lib_dir}:{existing}" if existing else str(lib_dir)

    return env


def generate_with_isaac_runtime(request: ScenarioGenerationRequest) -> list[GeneratedVariantArtifact]:
    isaac_python = _resolve_isaac_python()
    log_dir = OUTPUT_LOGS / request.job_id
    log_dir.mkdir(parents=True, exist_ok=True)

    request_path = log_dir / f"{request.job_id}_isaac_request.json"
    summary_path = log_dir / f"{request.job_id}_isaac_summary.json"
    write_json(request_path, request)

    cmd = [
        isaac_python,
        str(PROJECT_ROOT / "apps/simulator/isaac_standalone.py"),
        "--request-json",
        str(request_path),
        "--summary-json",
        str(summary_path),
    ]
    completed = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=_build_isaac_env(isaac_python),
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Isaac standalone generation failed.\n"
            f"Command: {' '.join(cmd)}\n"
            f"stdout:\n{completed.stdout[-4000:]}\n"
            f"stderr:\n{completed.stderr[-4000:]}"
        )
    if not summary_path.exists():
        raise RuntimeError("Isaac standalone run finished without writing a summary file.")

    payload = read_json(summary_path)
    generated = payload.get("generated_variants", [])
    if not generated:
        raise RuntimeError("Isaac standalone run did not return any generated variants.")
    return [GeneratedVariantArtifact(**artifact) for artifact in generated]
