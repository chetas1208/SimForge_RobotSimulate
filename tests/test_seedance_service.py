"""Tests for the Seedance preview prompt pipeline."""

from apps.runner.preview_services.seedance.service import SeedancePreviewService


def test_clean_llm_text_strips_wrappers():
    service = SeedancePreviewService(llm_provider="disabled")
    raw = 'Here is a detailed video generation prompt:\n\n**Prompt:** "Cinematic warehouse CCTV shot of an AMR turning into a blind corner."'
    assert service._clean_llm_text(raw) == "Cinematic warehouse CCTV shot of an AMR turning into a blind corner."


def test_clean_llm_text_strips_scene_description_label():
    service = SeedancePreviewService(llm_provider="disabled")
    raw = "Scene Description** The warehouse aisle is viewed from overhead while a robot approaches a forklift."
    assert service._clean_llm_text(raw) == "The warehouse aisle is viewed from overhead while a robot approaches a forklift."


def test_fallback_scene_description_uses_generated_scene_details():
    service = SeedancePreviewService(llm_provider="disabled")
    scenario_config = {
        "environment_template": "warehouse_aisle",
        "lighting_preset": "poor",
        "robot_path_type": "left_turn_blind_corner",
        "camera_mode": "overhead",
        "obstacle_count": 3,
        "forklift_count": 1,
        "dropped_object": True,
        "crossing_event": True,
    }
    manifest = {
        "environment_preset": "warehouse_aisle",
        "lighting_level": "poor",
        "camera_view": "overhead",
        "parsed_scenario": {
            "blind_corner": True,
            "pedestrian_count": 2,
            "forklift_count": 1,
        },
    }

    description = service._fallback_scene_description(scenario_config, manifest)

    assert "warehouse aisle" in description
    assert "poor lighting" in description
    assert "2 pedestrian workers" in description
    assert "blind-corner visibility problem" in description


def test_extract_seedance_generation_id_supports_nested_payload():
    service = SeedancePreviewService(llm_provider="disabled")
    payload = {"success": True, "data": {"video_id": "vid_123"}}
    assert service._extract_seedance_generation_id(payload) == "vid_123"


def test_normalize_seedance_status_supports_nested_payload():
    service = SeedancePreviewService(llm_provider="disabled")
    payload = {"success": True, "data": {"status": "completed", "video_url": "https://cdn.example/video.mp4"}}
    assert service._normalize_seedance_status(payload) == {
        "status": "completed",
        "video_url": "https://cdn.example/video.mp4",
        "error": None,
    }
