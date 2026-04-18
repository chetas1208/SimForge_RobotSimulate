"""Backend adapter for text-based warehouse safety requests."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.inference.service import WarehouseSafetyService


def run_text_scenario_job(
    description: str,
    job_id: str,
    model_dir: str,
    num_variants: int = 1,
    use_isaac: bool = True,
):
    service = WarehouseSafetyService(model_dir=model_dir)
    return service.process_description(
        description=description,
        job_id=job_id,
        num_variants=num_variants,
        use_isaac=use_isaac,
    )

