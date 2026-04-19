"""Seed database with realistic demo data."""

import uuid
import random
from datetime import timedelta

from app.core.time import utc_now
from app.db.database import SessionLocal
from app.db.models import (
    Scenario, ScenarioVariant, SimulationJob, OutputArtifact,
    EvaluationReport, ActivityLog, SystemSetting,
)


def _uid():
    return str(uuid.uuid4())


def seed_database():
    """Populate database with demo-quality seed data."""
    db = SessionLocal()
    try:
        # Skip if already seeded
        if db.query(Scenario).count() > 0:
            db.close()
            return

        now = utc_now()
        rng = random.Random(42)

        # ── Scenarios ──
        s1_id = _uid()
        s2_id = _uid()
        s3_id = _uid()

        scenarios = [
            Scenario(
                id=s1_id,
                name="Blind Corner Human Crossing",
                description="AMR approaches a blind corner while a human crosses late into the robot's path. Tests reaction time and collision avoidance.",
                environment_template="warehouse_aisle",
                robot_path_type="left_turn_blind_corner",
                human_crossing_probability=0.8,
                dropped_obstacle_level="medium",
                blocked_aisle_enabled=True,
                lighting_preset="low_light",
                camera_mode="overhead",
                variant_count=5,
                random_seed=42,
                status="completed",
                created_at=now - timedelta(hours=12),
            ),
            Scenario(
                id=s2_id,
                name="Dropped Box Obstruction",
                description="Fallen inventory creates unexpected obstacles in narrow aisle. Tests path replanning and obstacle detection.",
                environment_template="warehouse_aisle",
                robot_path_type="straight_aisle",
                human_crossing_probability=0.3,
                dropped_obstacle_level="high",
                blocked_aisle_enabled=False,
                lighting_preset="normal",
                camera_mode="follow",
                variant_count=3,
                random_seed=123,
                status="compiled",
                created_at=now - timedelta(hours=6),
            ),
            Scenario(
                id=s3_id,
                name="T-Junction Timing Conflict",
                description="Multiple AMRs and a human converge at T-junction simultaneously. Tests priority resolution and safety margins.",
                environment_template="warehouse_aisle",
                robot_path_type="t_junction",
                human_crossing_probability=0.6,
                dropped_obstacle_level="low",
                blocked_aisle_enabled=False,
                lighting_preset="high_contrast",
                camera_mode="multi_view",
                variant_count=4,
                random_seed=777,
                status="running",
                created_at=now - timedelta(hours=2),
            ),
        ]
        db.add_all(scenarios)

        # ── Variants for S1 ──
        variants = []
        for i in range(5):
            v_id = _uid()
            seed = 42 + i * 1000 + 7
            status = "completed" if i < 4 else "failed"
            variants.append(ScenarioVariant(
                id=v_id,
                scenario_id=s1_id,
                variant_index=i,
                variant_parameters_json={
                    "variant_index": i,
                    "human_present": rng.random() < 0.8,
                    "human_speed": round(rng.uniform(0.8, 2.0), 2),
                    "path_conflict_intensity": round(rng.uniform(0.3, 0.9), 2),
                    "obstacle_count": rng.randint(0, 3),
                    "visibility_modifier": rng.choice([0.7, 0.8, 0.9, 1.0]),
                    "hazard_severity": rng.choice(["low", "medium", "high", "critical"]),
                    "aisle_blocked": rng.random() < 0.6,
                    "robot_speed_modifier": round(rng.uniform(0.7, 1.3), 2),
                },
                deterministic_seed=seed,
                status=status,
            ))
        # Variants for S2
        for i in range(3):
            variants.append(ScenarioVariant(
                id=_uid(),
                scenario_id=s2_id,
                variant_index=i,
                variant_parameters_json={
                    "variant_index": i,
                    "human_present": rng.random() < 0.3,
                    "obstacle_count": rng.randint(1, 5),
                    "path_conflict_intensity": round(rng.uniform(0.1, 0.6), 2),
                    "hazard_severity": rng.choice(["medium", "high"]),
                },
                deterministic_seed=123 + i * 1000 + 7,
                status="queued",
            ))
        db.add_all(variants)

        # ── Jobs ──
        jobs = []
        s1_variants = [v for v in variants if v.scenario_id == s1_id]
        for i, v in enumerate(s1_variants):
            j_id = _uid()
            if i < 3:
                status = "completed"
                started = now - timedelta(hours=11, minutes=30 - i * 10)
                completed = started + timedelta(minutes=rng.randint(2, 8))
                duration = (completed - started).total_seconds()
                error = None
            elif i == 3:
                status = "running"
                started = now - timedelta(minutes=5)
                completed = None
                duration = None
                error = None
            else:
                status = "failed"
                started = now - timedelta(hours=10)
                completed = started + timedelta(seconds=45)
                duration = 45.0
                error = "Simulation timeout: actor collision detected at frame 312"
            jobs.append(SimulationJob(
                id=j_id,
                scenario_id=s1_id,
                variant_id=v.id,
                provider_type="mock",
                mode="mock",
                status=status,
                submitted_at=now - timedelta(hours=12),
                started_at=started,
                completed_at=completed,
                duration_seconds=duration,
                error_message=error,
            ))
        db.add_all(jobs)
        db.flush()

        # ── Artifacts for completed jobs ──
        artifacts = []
        completed_jobs = [j for j in jobs if j.status == "completed"]
        for j in completed_jobs:
            for atype, fname in [
                ("preview_image", f"preview_{j.id[:8]}.png"),
                ("manifest_json", f"manifest_{j.id[:8]}.json"),
                ("labels_json", f"labels_{j.id[:8]}.json"),
                ("evaluation_json", f"eval_{j.id[:8]}.json"),
                ("log_file", f"log_{j.id[:8]}.txt"),
            ]:
                artifacts.append(OutputArtifact(
                    id=_uid(),
                    job_id=j.id,
                    artifact_type=atype,
                    file_path=f"/storage/artifacts/{fname}",
                    preview_path=f"/storage/previews/{fname}" if "preview" in atype else None,
                    metadata_json={"scenario": s1_id, "generated": "mock"},
                ))
        db.add_all(artifacts)

        # ── Evaluations for completed jobs ──
        evals = []
        for j in completed_jobs:
            evals.append(EvaluationReport(
                id=_uid(),
                job_id=j.id,
                collision_risk_score=round(rng.uniform(0.2, 0.85), 3),
                occlusion_score=round(rng.uniform(0.1, 0.7), 3),
                path_conflict_score=round(rng.uniform(0.3, 0.9), 3),
                severity_score=round(rng.uniform(0.2, 0.8), 3),
                diversity_score=round(rng.uniform(0.4, 0.95), 3),
                coverage_summary_json={
                    "lighting_tested": True,
                    "human_scenarios": True,
                    "obstacle_levels": ["medium", "high"],
                },
                explanation="Overall severity: MODERATE. Collision risk elevated due to blind corner approach combined with late human crossing. Occlusion from obstacles reduces sensor coverage.",
                top_risk_factors=rng.sample([
                    "Human in blind spot", "Late crossing", "Low visibility",
                    "Blocked aisle", "Speed threshold exceeded",
                ], 3),
                recommended_actions=rng.sample([
                    "Review blind-corner thresholds", "Add safety margins",
                    "Increase sensor coverage", "Test higher obstacle density",
                ], 2),
            ))
        db.add_all(evals)

        # ── Activity Logs ──
        log_events = [
            ("scenario_created", "scenario", s1_id, "Scenario 'Blind Corner Human Crossing' created", now - timedelta(hours=12)),
            ("scenario_compiled", "scenario", s1_id, "Compiled 5 variants for scenario", now - timedelta(hours=11, minutes=50)),
            ("run_submitted", "scenario", s1_id, "Simulation run submitted with 5 jobs", now - timedelta(hours=11, minutes=45)),
            ("job_completed", "job", jobs[0].id, "Job completed successfully (3m 24s)", now - timedelta(hours=11, minutes=20)),
            ("job_completed", "job", jobs[1].id, "Job completed successfully (4m 12s)", now - timedelta(hours=11, minutes=10)),
            ("job_completed", "job", jobs[2].id, "Job completed successfully (2m 58s)", now - timedelta(hours=10, minutes=50)),
            ("job_failed", "job", jobs[4].id, "Job failed: Simulation timeout at frame 312", now - timedelta(hours=10)),
            ("scenario_created", "scenario", s2_id, "Scenario 'Dropped Box Obstruction' created", now - timedelta(hours=6)),
            ("scenario_compiled", "scenario", s2_id, "Compiled 3 variants for scenario", now - timedelta(hours=5, minutes=50)),
            ("scenario_created", "scenario", s3_id, "Scenario 'T-Junction Timing Conflict' created", now - timedelta(hours=2)),
            ("job_started", "job", jobs[3].id, "Job started running", now - timedelta(minutes=5)),
            ("system_info", None, None, "MockSimulationProvider initialized", now - timedelta(hours=12, minutes=5)),
        ]
        for etype, entity_type, entity_id, msg, ts in log_events:
            db.add(ActivityLog(
                id=_uid(),
                event_type=etype,
                related_entity_type=entity_type,
                related_entity_id=entity_id,
                message=msg,
                created_at=ts,
            ))

        # ── System Settings ──
        settings_data = [
            ("simulation_provider", "mock"),
            ("default_variant_count", "5"),
            ("output_storage_path", "./storage"),
            ("hpc_enabled", "false"),
            ("hpc_host", ""),
            ("hpc_user", ""),
            ("max_concurrent_jobs", "4"),
        ]
        for key, value in settings_data:
            db.add(SystemSetting(id=_uid(), key=key, value=value))

        db.commit()
        print("[SimForge] ✓ Database seeded with demo data")
    except Exception as e:
        db.rollback()
        print(f"[SimForge] Seed error: {e}")
    finally:
        db.close()
