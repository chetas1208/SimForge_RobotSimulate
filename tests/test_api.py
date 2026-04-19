"""Tests for SimForge Backend API."""

import io
import os
import sys
import uuid
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "simforge-sdk"))

# Use a test database
os.environ["DATABASE_URL"] = "sqlite:///./test_simforge.db"

from app.db.database import SessionLocal, init_db
from app.db.models import EvaluationReport, OutputArtifact, Scenario, ScenarioVariant, SimulationJob
from main import app

# Initialize database for tests
init_db()

client = TestClient(app)


def _cleanup_scenario(scenario_id: str):
    db = SessionLocal()
    try:
        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if scenario:
            db.delete(scenario)
            db.commit()
    finally:
        db.close()


def _seed_completed_scenario(tmp_path: Path) -> dict:
    scenario_id = str(uuid.uuid4())
    variant_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    artifact_id = str(uuid.uuid4())
    eval_artifact_id = str(uuid.uuid4())

    preview_path = tmp_path / "preview.mp4"
    preview_path.write_bytes(b"fake-video")
    evaluation_path = tmp_path / "evaluation.json"
    evaluation_path.write_text('{"status":"ok"}', encoding="utf-8")

    db = SessionLocal()
    try:
        db.add(
            Scenario(
                id=scenario_id,
                name="Completed Scenario",
                environment_template="warehouse_aisle",
                robot_path_type="left_turn_blind_corner",
                variant_count=1,
                random_seed=42,
                status="completed",
            )
        )
        db.add(
            ScenarioVariant(
                id=variant_id,
                scenario_id=scenario_id,
                variant_index=0,
                variant_parameters_json={"timing_offset_s": 0.5},
                deterministic_seed=42,
                status="completed",
            )
        )
        db.add(
            SimulationJob(
                id=job_id,
                scenario_id=scenario_id,
                variant_id=variant_id,
                provider_type="track4",
                mode="track4",
                status="completed",
                log_path=str(tmp_path / "job.log"),
            )
        )
        db.add(
            EvaluationReport(
                id=str(uuid.uuid4()),
                job_id=job_id,
                collision_risk_score=0.82,
                occlusion_score=0.41,
                path_conflict_score=0.37,
                severity_score=0.55,
                diversity_score=1.0,
                coverage_summary_json={"environment_type": "warehouse"},
                explanation="Blind corner with limited clearance.",
                top_risk_factors=["occlusion", "cross-traffic"],
                recommended_actions=["Reduce robot speed"],
            )
        )
        db.add(
            OutputArtifact(
                id=artifact_id,
                job_id=job_id,
                artifact_type="preview_video",
                file_path=str(preview_path),
                preview_path=str(preview_path),
                metadata_json={"scenario_id": scenario_id, "variant_index": 0},
            )
        )
        db.add(
            OutputArtifact(
                id=eval_artifact_id,
                job_id=job_id,
                artifact_type="evaluation_json",
                file_path=str(evaluation_path),
                metadata_json={"scenario_id": scenario_id, "variant_index": 0},
            )
        )
        db.commit()
    finally:
        db.close()

    return {
        "scenario_id": scenario_id,
        "variant_id": variant_id,
        "job_id": job_id,
        "artifact_id": artifact_id,
        "preview_path": preview_path,
    }


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "simforge-api"


class TestScenarioEndpoints:
    def test_list_scenarios(self):
        response = client.get("/api/scenarios")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_scenario(self):
        data = {
            "name": "API Test Scenario",
            "description": "Created from test",
            "environment_template": "warehouse_aisle",
            "robot_path_type": "t_junction",
            "variant_count": 3,
            "random_seed": 100,
        }
        response = client.post("/api/scenarios", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["name"] == "API Test Scenario"
        assert result["variant_count"] == 3

    def test_get_scenario(self):
        # First create one
        scenarios = client.get("/api/scenarios").json()
        if scenarios:
            sid = scenarios[0]["id"]
            response = client.get(f"/api/scenarios/{sid}")
            assert response.status_code == 200
            assert response.json()["id"] == sid

    def test_update_scenario(self):
        scenarios = client.get("/api/scenarios").json()
        if scenarios:
            sid = scenarios[0]["id"]
            response = client.put(f"/api/scenarios/{sid}", json={"notes": "updated"})
            assert response.status_code == 200

    def test_compile_scenario(self):
        scenarios = client.get("/api/scenarios").json()
        if scenarios:
            sid = scenarios[0]["id"]
            response = client.post(f"/api/scenarios/{sid}/compile")
            assert response.status_code == 200
            variants = response.json()
            assert isinstance(variants, list)
            assert len(variants) > 0

    def test_get_variants(self):
        scenarios = client.get("/api/scenarios").json()
        if scenarios:
            sid = scenarios[0]["id"]
            response = client.get(f"/api/scenarios/{sid}/variants")
            assert response.status_code == 200

    def test_delete_scenario(self):
        # Create a scenario to delete
        data = {"name": "To Delete", "variant_count": 1}
        created = client.post("/api/scenarios", json=data).json()
        response = client.delete(f"/api/scenarios/{created['id']}")
        assert response.status_code == 200
        assert response.json()["deleted"] is True

    def test_get_nonexistent_scenario(self):
        response = client.get("/api/scenarios/nonexistent-id")
        assert response.status_code == 404


class TestJobEndpoints:
    def test_list_jobs(self):
        response = client.get("/api/jobs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_nonexistent_job(self):
        response = client.get("/api/jobs/nonexistent-id")
        assert response.status_code == 404


class TestArtifactEndpoints:
    def test_list_artifacts(self):
        response = client.get("/api/artifacts")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_download_artifact(self, tmp_path):
        seeded = _seed_completed_scenario(tmp_path)
        try:
            response = client.get(f"/api/artifacts/{seeded['artifact_id']}/download")
            assert response.status_code == 200
            assert response.headers["content-type"] == "video/mp4"
            assert response.content == seeded["preview_path"].read_bytes()
        finally:
            _cleanup_scenario(seeded["scenario_id"])


class TestEvaluationEndpoints:
    def test_list_evaluations(self):
        response = client.get("/api/evaluations")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestActivityEndpoints:
    def test_list_activity(self):
        response = client.get("/api/activity")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestSettingsEndpoints:
    def test_get_settings(self):
        response = client.get("/api/settings")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


class TestIntegrationFlow:
    """Integration test: scenario -> compile -> run -> check."""

    def test_full_workflow(self):
        # 1. Create scenario
        scenario_data = {
            "name": "Integration Test Scenario",
            "environment_template": "warehouse_aisle",
            "robot_path_type": "left_turn_blind_corner",
            "human_crossing_probability": 0.8,
            "variant_count": 2,
            "random_seed": 42,
        }
        create_resp = client.post("/api/scenarios", json=scenario_data)
        assert create_resp.status_code == 200
        scenario_id = create_resp.json()["id"]

        # 2. Compile variants
        compile_resp = client.post(f"/api/scenarios/{scenario_id}/compile")
        assert compile_resp.status_code == 200
        variants = compile_resp.json()
        assert len(variants) == 2

        # 3. Submit run
        run_resp = client.post(f"/api/scenarios/{scenario_id}/run")
        assert run_resp.status_code == 200
        run_data = run_resp.json()
        assert len(run_data["job_ids"]) == 2
        assert run_data["status"] == "queued"

        # 4. Check jobs exist
        jobs_resp = client.get("/api/jobs")
        assert jobs_resp.status_code == 200

        # 5. Check scenario status updated
        scenario_resp = client.get(f"/api/scenarios/{scenario_id}")
        assert scenario_resp.status_code == 200

        # Cleanup
        client.delete(f"/api/scenarios/{scenario_id}")

    def test_scenario_results_payload(self, tmp_path):
        seeded = _seed_completed_scenario(tmp_path)
        try:
            response = client.get(f"/api/scenarios/{seeded['scenario_id']}/results")
            assert response.status_code == 200
            payload = response.json()
            assert payload["scenario"]["id"] == seeded["scenario_id"]
            assert payload["summary"]["variant_count"] == 1
            assert payload["summary"]["completed_jobs"] == 1
            assert payload["summary"]["highest_risk_variant"]["variant_id"] == seeded["variant_id"]

            variant_result = payload["variant_results"][0]
            assert variant_result["job"]["id"] == seeded["job_id"]
            assert variant_result["evaluation"]["collision_risk_score"] == 0.82
            assert len(variant_result["artifacts"]) == 2
            assert all(artifact["download_url"].startswith("/api/artifacts/") for artifact in variant_result["artifacts"])
        finally:
            _cleanup_scenario(seeded["scenario_id"])

    def test_export_scenario_results(self, tmp_path):
        seeded = _seed_completed_scenario(tmp_path)
        try:
            response = client.get(f"/api/scenarios/{seeded['scenario_id']}/export")
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/zip"

            archive = zipfile.ZipFile(io.BytesIO(response.content))
            names = set(archive.namelist())
            assert "scenario_results.json" in names
            assert "variants/variant_00/variant.json" in names
            assert "variants/variant_00/evaluation.json" in names
            assert any(name.endswith("/artifacts/preview_video_preview.mp4") for name in names)
            assert any(name.endswith("/artifacts/evaluation_json_evaluation.json") for name in names)
        finally:
            _cleanup_scenario(seeded["scenario_id"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
