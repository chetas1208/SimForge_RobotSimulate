"""Seedance preview service for high-quality concept video generation."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import requests
from openai import OpenAI


class SeedancePreviewService:
    """
    Generate concept preview videos using LLM + video generation API.
    
    This service:
    1. Converts scenario config to detailed prompt
    2. Enhances prompt with LLM (GPT-4)
    3. Calls video generation API (Seedance/Runway)
    4. Downloads and stores video
    
    IMPORTANT: These are CONCEPT PREVIEWS, not simulation truth.
    """
    
    def __init__(
        self,
        seedance_api_key: str | None = None,
        llm_provider: str = "nvidia_nim",
        nvidia_nim_api_key: str | None = None,
        video_provider: str = "seedance",
    ):
        self.seedance_api_key = seedance_api_key or os.getenv("SEEDANCE_API_KEY")
        self.llm_provider = llm_provider or os.getenv("LLM_PROVIDER", "nvidia_nim")
        self.nvidia_nim_api_key = nvidia_nim_api_key or os.getenv("NVIDIA_NIM_API_KEY")
        self.nvidia_nim_base_url = os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self.video_provider = video_provider
    
    def generate_preview(
        self,
        scenario_config: dict[str, Any],
        manifest: dict[str, Any],
        output_path: str | Path,
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
        # Step 1: Create base prompt
        base_prompt = self._create_video_prompt(scenario_config)
        
        # Step 2: Enhance with LLM (if available)
        if self.openai_client:
            enhanced_prompt = self._enhance_with_llm(base_prompt, scenario_config)
        else:
            enhanced_prompt = base_prompt
        
        # Step 3: Generate video
        video_url = self._generate_video(enhanced_prompt)
        
        # Step 4: Download video
        video_path = self._download_video(video_url, output_path)
        
        return {
            "video_path": str(video_path),
            "preview_type": "concept_preview_video",
            "source": self.video_provider,
            "label": "AI-Generated Concept Preview - Not Simulation Truth",
            "metadata": {
                "base_prompt": base_prompt,
                "enhanced_prompt": enhanced_prompt,
                "video_provider": self.video_provider,
                "scenario_id": manifest.get("scenario_id"),
                "variant_index": manifest.get("variant_index"),
            }
        }
    
    def _create_video_prompt(self, config: dict[str, Any]) -> str:
        """Convert scenario config to video generation prompt."""
        environment = config.get("environment_template", "warehouse_aisle")
        lighting = config.get("lighting_preset", "normal")
        robot_path = config.get("robot_path_type", "straight_aisle")
        obstacles = config.get("dropped_obstacle_level", "medium")
        human_prob = config.get("human_crossing_probability", 0.5)
        camera = config.get("camera_mode", "overhead")
        blind_corner = config.get("blind_corner_enabled", False)
        
        # Build detailed prompt
        prompt_parts = [
            f"Warehouse safety scenario video:",
            f"- Environment: {environment.replace('_', ' ')}",
            f"- Lighting: {lighting} lighting conditions",
            f"- Robot: autonomous mobile robot (AMR) navigating {robot_path.replace('_', ' ')}",
        ]
        
        if blind_corner:
            prompt_parts.append("- Hazard: blind corner with limited visibility")
        
        if obstacles != "none":
            prompt_parts.append(f"- Obstacles: {obstacles} level of dropped boxes and clutter")
        
        if human_prob > 0.3:
            prompt_parts.append(f"- Humans: warehouse workers crossing robot path")
        
        prompt_parts.extend([
            f"- Camera: {camera.replace('_', ' ')} view",
            "- Duration: 10 seconds",
            "- Style: realistic warehouse CCTV footage, industrial setting",
        ])
        
        return "\n".join(prompt_parts)
    
    def _enhance_with_llm(self, base_prompt: str, config: dict[str, Any]) -> str:
        """Use LLM to create detailed video generation prompt."""
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
            system_prompt = """You are an expert at creating detailed prompts for video generation APIs.
Convert warehouse safety scenarios into vivid, specific video descriptions that will produce realistic warehouse footage.
Focus on:
- Specific visual details (lighting, textures, movement)
- Camera angles and framing
- Realistic warehouse environment details
- Safety-critical moments and hazards
- Industrial/CCTV aesthetic

Keep the prompt under 500 characters for video generation API limits."""

            response = requests.post(
                f"{self.nvidia_nim_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.nvidia_nim_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "meta/llama-3.1-70b-instruct",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Create a detailed video generation prompt for:\n\n{base_prompt}"}
                    ],
                    "max_tokens": 200,
                    "temperature": 0.7,
                },
                timeout=30,
            )
            response.raise_for_status()
            
            enhanced = response.json()["choices"][0]["message"]["content"].strip()
            
            # Ensure it's not too long for video APIs
            if len(enhanced) > 500:
                enhanced = enhanced[:497] + "..."
            
            print(f"✅ NVIDIA NIM enhanced prompt: {enhanced[:100]}...")
            return enhanced
            
        except Exception as e:
            print(f"NVIDIA NIM enhancement failed: {e}, using base prompt")
            return base_prompt
    
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
        
        # Submit generation request
        response = requests.post(
            f"{seedance_base_url}/generate",
            headers={
                "Authorization": f"Bearer {self.seedance_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "prompt": prompt,
                "duration": 10,
                "resolution": "1280x720",
                "style": "realistic",
                "fps": 24,
            },
            timeout=30,
        )
        response.raise_for_status()
        
        generation_id = response.json()["id"]
        print(f"   Generation ID: {generation_id}")
        
        # Poll for completion
        max_wait = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status_response = requests.get(
                f"{seedance_base_url}/generate/{generation_id}",
                headers={"Authorization": f"Bearer {self.seedance_api_key}"},
                timeout=10,
            )
            status_response.raise_for_status()
            
            status_data = status_response.json()
            
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
            response = requests.get(
                f"https://api.seedance.ai/v1/generate/{generation_id}",
                headers={"Authorization": f"Bearer {self.seedance_api_key}"},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        else:
            raise NotImplementedError(f"Status check not implemented for {self.video_provider}")
