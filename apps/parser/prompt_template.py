"""Optional prompt template for an LLM-based text-to-scenario parser."""

LLM_SCENARIO_PARSER_PROMPT = """You convert warehouse safety scenario descriptions into strict JSON.

Rules:
- Return JSON only.
- Use this schema exactly:
  {
    "environment": "warehouse_aisle|narrow_corridor|loading_zone|blind_corner_aisle",
    "lighting": "bright|normal|low|poor|emergency",
    "blind_corner": true|false,
    "pedestrian_count": integer 0-10,
    "forklift_count": integer 0-5,
    "obstacle_density": "low|medium|high",
    "camera_view": "overhead|follow|fixed_angle|first_person|multi_view",
    "difficulty": "easy|medium|hard|critical",
    "reflective_floor": true|false,
    "robot_speed_mps": number,
    "pedestrian_speed_mps": number,
    "num_variants": integer 1-32,
    "dropped_object": true|false,
    "crossing_event": true|false,
    "description": "original user text"
  }
- Fill reasonable defaults when the user omits details.
- Reject impossible combinations by returning:
  {"error": "reason"}
"""

