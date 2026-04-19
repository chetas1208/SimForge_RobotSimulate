"""Seedance preview service for high-quality concept video generation."""

from __future__ import annotations

import os
import time
import json
import re
from pathlib import Path
from typing import Any

import requests


class SeedancePreviewService:
    """
    Generate concept preview videos using LLM + video generation API.
    
    This service:
    1. Converts scenario config to detailed prompt
    2. Enhances prompt with LLM
    3. Calls video generation API (Seedance/Runway)
    4. Downloads and stores video
    
    IMPORTANT: These are CONCEPT PREVIEWS, not simulation truth.
    """
    
    def __init__(
        self,
        seedance_api_key: str | None = None,
        llm_provider: str = "nvidia_nim",
        nvidia_nim_api_key: str | None = None,
        nvidia_nim_model: str | None = None,
        nvidia_nim_usd_model: str | None = None,
        video_provider: str = "seedance",
    ):
        self.seedance_api_key = seedance_api_key or os.getenv("SEEDANCE_API_KEY")
        self.llm_provider = (llm_provider or os.getenv("LLM_PROVIDER", "nvidia_nim")).strip().lower()
        self.nvidia_nim_api_key = nvidia_nim_api_key or os.getenv("NVIDIA_NIM_API_KEY")
        self.nvidia_nim_base_url = os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self.nvidia_nim_model = (
            nvidia_nim_model
            or os.getenv("NVIDIA_NIM_MODEL")
            or "nvidia/llama-3.3-nemotron-super-49b-v1"
        )
        self.nvidia_nim_usd_model = (
            nvidia_nim_usd_model
            or os.getenv("NVIDIA_NIM_USD_MODEL")
            or self.nvidia_nim_model
        )
        self.video_provider = video_provider
    
    def generate_preview(
        self,
        scenario_config: dict[str, Any],
        manifest: dict[str, Any],
        output_path: str | Path,
        scene_usda: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate concept preview video from scenario.
        
        Returns:
            {
                "video_path": str,
                "preview_type": "concept_preview_video",
                "source": "seedance",
                "label": "AI-Generated Concept Preview",
                "metadata": {...}
            }
        """
        # Step 1: Turn simulator output into a scene description.
        scene_description = self._describe_scene(
            scenario_config=scenario_config,
            manifest=manifest,
            scene_usda=scene_usda,
        )

        # Step 2: Create the initial video prompt from the scene description.
        base_prompt = self._create_video_prompt(scene_description)
        
        # Step 3: Enhance with LLM (if available)
        enhanced_prompt = self._enhance_with_llm(base_prompt)
        
        # Step 4: Generate video
        video_url = self._generate_video(enhanced_prompt)
        
        # Step 5: Download video
        video_path = self._download_video(video_url, output_path)
        
        return {
            "video_path": str(video_path),
            "preview_type": "concept_preview_video",
            "source": self.video_provider,
            "label": "AI-Generated Concept Preview - Not Simulation Truth",
            "metadata": {
                "scene_description": scene_description,
                "base_prompt": base_prompt,
                "enhanced_prompt": enhanced_prompt,
                "video_provider": self.video_provider,
                "scenario_id": manifest.get("scenario_id"),
                "variant_index": manifest.get("variant_index"),
            }
        }
    
    def _describe_scene(
        self,
        scenario_config: dict[str, Any],
        manifest: dict[str, Any],
        scene_usda: str | None,
    ) -> str:
        """Build a plain-English scene description from OpenUSD, with a deterministic fallback."""
        fallback = self._fallback_scene_description(scenario_config, manifest)
        if self.llm_provider != "nvidia_nim" or not self.nvidia_nim_api_key or not scene_usda:
            return fallback

        system_prompt = (
            "You are an expert OpenUSD scene analyst for warehouse robotics simulations. "
            "Read the provided USDA scene and manifest, then write a short plain-English scene description "
            "in 3 to 5 sentences. Mention environment layout, lighting, camera viewpoint, robot motion, "
            "humans, forklifts, obstacles, and the primary safety hazard. Return plain text only."
        )
        user_prompt = (
            f"Manifest JSON:\n{json.dumps(manifest, indent=2, sort_keys=True)}\n\n"
            f"Scenario Config JSON:\n{json.dumps(scenario_config, indent=2, sort_keys=True)}\n\n"
            f"OpenUSD Scene (USDA):\n{scene_usda}"
        )

        try:
            description = self._chat_completion(
                model=self.nvidia_nim_usd_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=250,
                temperature=0.2,
            )
            cleaned = self._clean_llm_text(description)
            return cleaned or fallback
        except Exception as exc:
            print(f"OpenUSD scene description failed with USD-tuned model: {exc}")
            if self.nvidia_nim_usd_model != self.nvidia_nim_model:
                try:
                    description = self._chat_completion(
                        model=self.nvidia_nim_model,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        max_tokens=250,
                        temperature=0.2,
                    )
                    cleaned = self._clean_llm_text(description)
                    if cleaned:
                        return cleaned
                except Exception as fallback_exc:
                    print(f"OpenUSD scene description fallback model failed: {fallback_exc}")
            print("Using deterministic fallback scene description")
            return fallback

    def _fallback_scene_description(self, scenario_config: dict[str, Any], manifest: dict[str, Any]) -> str:
        """Create a deterministic scene description when the USD-aware LLM path is unavailable."""
        parsed = manifest.get("parsed_scenario") or {}
        environment = str(manifest.get("environment_preset") or scenario_config.get("environment_template", "warehouse_aisle")).replace("_", " ")
        lighting = str(manifest.get("lighting_level") or parsed.get("lighting") or scenario_config.get("lighting_preset", "normal")).replace("_", " ")
        camera = str(manifest.get("camera_view") or parsed.get("camera_view") or scenario_config.get("camera_mode", "overhead")).replace("_", " ")
        robot_path = str(scenario_config.get("robot_path_type", "straight_aisle")).replace("_", " ")
        human_count = int(parsed.get("pedestrian_count", scenario_config.get("human_count", 0)) or 0)
        forklift_count = int(parsed.get("forklift_count", scenario_config.get("forklift_count", 0)) or 0)
        obstacle_count = int(scenario_config.get("obstacle_count", 0) or 0)
        blind_corner = bool(parsed.get("blind_corner") or scenario_config.get("blind_corner") or "blind_corner" in str(scenario_config.get("robot_path_type", "")))
        dropped_object = bool(scenario_config.get("dropped_object") or scenario_config.get("dropped_obstacle_level") not in {None, "", "none"})
        crossing_event = bool(scenario_config.get("crossing_event") or scenario_config.get("human_crossing_probability", 0) > 0.2)

        details = [
            f"A warehouse safety simulation is staged in a {environment} under {lighting} lighting.",
            f"The camera is positioned in a {camera} view while an autonomous mobile robot follows a {robot_path} route.",
        ]
        if human_count:
            details.append(f"There are {human_count} pedestrian workers moving through the scene.")
        if forklift_count:
            details.append(f"There are {forklift_count} forklifts operating nearby.")
        if obstacle_count or dropped_object:
            details.append(
                f"The floor includes {max(obstacle_count, 1)} clutter or dropped-object hazards that tighten clearance."
            )
        hazards: list[str] = []
        if blind_corner:
            hazards.append("a blind-corner visibility problem")
        if crossing_event:
            hazards.append("a crossing conflict between robot and workers")
        if not hazards:
            hazards.append("a constrained warehouse traffic interaction")
        details.append(f"The main safety risk is {', '.join(hazards)}.")
        return " ".join(details)

    def _create_video_prompt(self, scene_description: str) -> str:
        """Convert the scene description into an initial video prompt brief."""
        return (
            "AI-generated concept preview video for a warehouse robotics safety scenario. "
            f"{scene_description} "
            "Use a realistic industrial warehouse look, subtle camera motion, natural worker movement, "
            "and emphasize the key near-miss hazard. Duration 10 seconds, 16:9, photorealistic CCTV/documentary style."
        )
    
    def _enhance_with_llm(self, base_prompt: str) -> str:
        """Use LLM to create detailed video generation prompt."""
        if self.llm_provider in {"", "none", "disabled"}:
            return base_prompt
        if self.llm_provider == "nvidia_nim":
            return self._enhance_with_nvidia_nim(base_prompt)
        else:
            return base_prompt
    
    def _enhance_with_nvidia_nim(self, base_prompt: str) -> str:
        """Use NVIDIA NIM API to enhance prompt."""
        if not self.nvidia_nim_api_key:
            print("NVIDIA NIM API key not set, using base prompt")
            return base_prompt
        
        try:
            system_prompt = (
                "You create short production-ready prompts for text-to-video models. "
                "Rewrite the input into one compact prompt under 500 characters. "
                "Return only the final prompt text with no markdown, no quotes, no labels, and no explanation. "
                "Keep the output photorealistic, cinematic, and grounded in warehouse robotics safety footage."
            )
            enhanced = self._chat_completion(
                model=self.nvidia_nim_model,
                system_prompt=system_prompt,
                user_prompt=base_prompt,
                max_tokens=180,
                temperature=0.45,
            )
            enhanced = self._clean_llm_text(enhanced)
            if len(enhanced) > 500:
                enhanced = enhanced[:497].rstrip(" ,.;:") + "..."
            print(f"✅ NVIDIA NIM enhanced prompt: {enhanced[:100]}...")
            return enhanced or base_prompt
            
        except Exception as e:
            print(f"NVIDIA NIM enhancement failed: {e}, using base prompt")
            return base_prompt

    def _chat_completion(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        response = requests.post(
            f"{self.nvidia_nim_base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.nvidia_nim_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=45,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    def _clean_llm_text(self, text: str) -> str:
        """Strip markdown wrappers and prompt labels from LLM output."""
        cleaned = text.strip()
        cleaned = cleaned.replace("```text", "").replace("```", "").strip()
        cleaned = re.sub(r"^Here is (a|the) .*?:\s*", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = cleaned.lstrip("* ").strip()
        cleaned = re.sub(
            r"^(scene description|description|video prompt)\*{0,2}\s*:?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"^Prompt\s*\*{0,2}:?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.lstrip("* ").strip()
        cleaned = cleaned.strip().strip('"').strip("'")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        quoted = re.findall(r'"([^"]{20,})"', cleaned)
        if quoted:
            cleaned = max(quoted, key=len).strip()
        return cleaned
    
    def _generate_video(self, prompt: str) -> str:
        """Call video generation API."""
        if self.video_provider == "seedance":
            return self._generate_seedance(prompt)
        elif self.video_provider == "runway":
            return self._generate_runway(prompt)
        else:
            raise ValueError(f"Unknown video provider: {self.video_provider}")
    
    def _generate_seedance(self, prompt: str) -> str:
        """Generate video using Seedance API."""
        if not self.seedance_api_key:
            raise ValueError("SEEDANCE_API_KEY not set")
        
        seedance_base_url = os.getenv("SEEDANCE_BASE_URL", "https://api.seedance.ai/v1")
        
        print(f"🎬 Generating video with Seedance...")
        print(f"   Prompt: {prompt[:100]}...")
        
        headers = {
            "Authorization": f"Bearer {self.seedance_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "prompt": prompt,
            "duration": 10,
            "resolution": "720p",
            "style": "cinematic",
            "fps": 24,
        }

        # Prefer the documented text-to-video route, but keep a fallback for older integrations.
        response = self._post_seedance(
            seedance_base_url=seedance_base_url,
            headers=headers,
            payload=payload,
        )
        response.raise_for_status()

        generation_id = self._extract_seedance_generation_id(response.json())
        print(f"   Generation ID: {generation_id}")
        
        # Poll for completion
        max_wait = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status_response = self._get_seedance_status(
                seedance_base_url=seedance_base_url,
                generation_id=generation_id,
                headers={"Authorization": f"Bearer {self.seedance_api_key}"},
            )
            status_response.raise_for_status()
            
            status_data = self._normalize_seedance_status(status_response.json())
            
            if status_data["status"] == "completed":
                video_url = status_data["video_url"]
                print(f"✅ Video generated: {video_url}")
                return video_url
            elif status_data["status"] == "failed":
                raise RuntimeError(f"Video generation failed: {status_data.get('error')}")
            
            elapsed = int(time.time() - start_time)
            print(f"   Status: {status_data['status']} ({elapsed}s elapsed)")
            time.sleep(5)
        
        raise TimeoutError("Video generation timed out")

    def _post_seedance(self, seedance_base_url: str, headers: dict[str, str], payload: dict[str, Any]) -> requests.Response:
        """Submit a text-to-video request using the latest known route, with backward compatibility."""
        response = requests.post(
            f"{seedance_base_url}/generate/text-to-video",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if response.status_code == 404:
            return requests.post(
                f"{seedance_base_url}/generate",
                headers=headers,
                json=payload,
                timeout=30,
            )
        return response

    def _extract_seedance_generation_id(self, payload: dict[str, Any]) -> str:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        generation_id = data.get("video_id") or data.get("id") or payload.get("video_id") or payload.get("id")
        if not generation_id:
            raise KeyError(f"Seedance response did not include a generation id: {payload}")
        return str(generation_id)

    def _get_seedance_status(
        self,
        seedance_base_url: str,
        generation_id: str,
        headers: dict[str, str],
    ) -> requests.Response:
        """Check generation status using the documented route, then a legacy fallback."""
        response = requests.get(
            f"{seedance_base_url}/video/{generation_id}/status",
            headers=headers,
            timeout=10,
        )
        if response.status_code == 404:
            return requests.get(
                f"{seedance_base_url}/generate/{generation_id}",
                headers=headers,
                timeout=10,
            )
        return response

    def _normalize_seedance_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        status = data.get("status", payload.get("status", "unknown"))
        video_url = (
            data.get("video_url")
            or payload.get("video_url")
            or data.get("url")
            or payload.get("url")
        )
        error = (
            data.get("error")
            or payload.get("error")
            or data.get("message")
            or payload.get("message")
        )
        return {
            "status": status,
            "video_url": video_url,
            "error": error,
        }
    
    def _generate_runway(self, prompt: str) -> str:
        """Generate video using Runway API (placeholder)."""
        # TODO: Implement Runway API integration
        raise NotImplementedError("Runway integration not yet implemented")
    
    def _download_video(self, video_url: str, output_path: str | Path) -> Path:
        """Download video from URL."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        response = requests.get(video_url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return output_path
    
    def get_status(self, generation_id: str) -> dict[str, Any]:
        """Check status of video generation."""
        if self.video_provider == "seedance":
            seedance_base_url = os.getenv("SEEDANCE_BASE_URL", "https://api.seedance.ai/v1")
            response = self._get_seedance_status(
                seedance_base_url=seedance_base_url,
                generation_id=generation_id,
                headers={"Authorization": f"Bearer {self.seedance_api_key}"},
            )
            response.raise_for_status()
            return self._normalize_seedance_status(response.json())
        else:
            raise NotImplementedError(f"Status check not implemented for {self.video_provider}")
