"""Simple headless preview renderer for scenario traces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from packages.shared_schema import ScenarioVariantConfig


CANVAS_WIDTH = 720
CANVAS_HEIGHT = 420


def render_preview(
    annotations: dict[str, Any],
    variant: ScenarioVariantConfig,
    destination_prefix: str | Path,
    fps: int = 12,
    stride: int = 2,
) -> tuple[Path, str]:
    try:
        import imageio.v2 as imageio
    except ImportError as exc:
        raise RuntimeError(
            "imageio is required for preview rendering. Install apps/simulator/requirements.txt first."
        ) from exc

    destination = Path(destination_prefix)
    destination.parent.mkdir(parents=True, exist_ok=True)

    frames = []
    for frame_index, frame in enumerate(annotations["frames"]):
        if frame_index % max(1, stride) != 0:
            continue
        frames.append(_render_frame(frame, annotations, variant))

    mp4_path = destination.with_suffix(".mp4")
    try:
        imageio.mimwrite(mp4_path, frames, fps=fps)
        return mp4_path, "preview_video"
    except Exception:
        gif_path = destination.with_suffix(".gif")
        imageio.mimsave(gif_path, frames, duration=max(0.05, 1.0 / max(fps, 1)))
        return gif_path, "preview_asset"


def _render_frame(frame: dict[str, Any], annotations: dict[str, Any], variant: ScenarioVariantConfig) -> np.ndarray:
    canvas = np.zeros((CANVAS_HEIGHT, CANVAS_WIDTH, 3), dtype=np.uint8)
    canvas[:] = _background_color(variant)
    _draw_environment(canvas, variant)

    static_objects = annotations.get("static_objects", [])
    for obj in static_objects:
        _draw_box(canvas, tuple(obj["position"]), size=(0.7, 0.7), color=(220, 148, 64))

    for position in frame.get("humans", []):
        _draw_circle(canvas, tuple(position), radius=0.28, color=(78, 192, 255))
    for position in frame.get("forklifts", []):
        _draw_box(canvas, tuple(position), size=(1.3, 0.7), color=(255, 192, 64))

    _draw_box(canvas, tuple(frame["robot"]), size=(0.9, 0.6), color=(90, 230, 140))

    if variant.camera_view.value == "multi_view":
        follow_view = canvas.copy()
        _highlight_follow_region(follow_view, tuple(frame["robot"]))
        canvas = np.concatenate([canvas[:, : CANVAS_WIDTH // 2], follow_view[:, CANVAS_WIDTH // 2 :]], axis=1)
    elif variant.camera_view.value in {"follow", "first_person"}:
        _highlight_follow_region(canvas, tuple(frame["robot"]))

    return canvas


def _draw_environment(canvas: np.ndarray, variant: ScenarioVariantConfig) -> None:
    floor_color = (52, 58, 72)
    if variant.reflective_floor:
        floor_color = (72, 78, 90)
    canvas[60:340, 120:360] = floor_color
    canvas[120:360, 300:540] = floor_color
    canvas[50:60, 120:360] = (20, 22, 28)
    canvas[340:350, 120:360] = (20, 22, 28)
    canvas[120:360, 540:550] = (20, 22, 28)
    canvas[120:130, 300:540] = (20, 22, 28)


def _highlight_follow_region(canvas: np.ndarray, robot_position: tuple[float, float]) -> None:
    px, py = _world_to_pixel(robot_position)
    x0 = max(px - 110, 0)
    x1 = min(px + 110, CANVAS_WIDTH)
    y0 = max(py - 90, 0)
    y1 = min(py + 90, CANVAS_HEIGHT)
    overlay = canvas.copy()
    overlay[y0:y1, x0:x1] = np.clip(overlay[y0:y1, x0:x1] + 28, 0, 255)
    canvas[:, :] = overlay


def _background_color(variant: ScenarioVariantConfig) -> tuple[int, int, int]:
    mapping = {
        "bright": (36, 40, 50),
        "normal": (24, 28, 36),
        "low": (18, 22, 30),
        "poor": (14, 16, 22),
        "emergency": (56, 26, 26),
    }
    return mapping[variant.lighting_level.value]


def _draw_box(canvas: np.ndarray, world_position: tuple[float, float], size: tuple[float, float], color: tuple[int, int, int]) -> None:
    px, py = _world_to_pixel(world_position)
    half_w = max(3, int(size[0] * 16))
    half_h = max(3, int(size[1] * 16))
    x0 = max(px - half_w, 0)
    x1 = min(px + half_w, CANVAS_WIDTH)
    y0 = max(py - half_h, 0)
    y1 = min(py + half_h, CANVAS_HEIGHT)
    canvas[y0:y1, x0:x1] = color


def _draw_circle(canvas: np.ndarray, world_position: tuple[float, float], radius: float, color: tuple[int, int, int]) -> None:
    px, py = _world_to_pixel(world_position)
    radius_px = max(3, int(radius * 20))
    y_grid, x_grid = np.ogrid[:CANVAS_HEIGHT, :CANVAS_WIDTH]
    mask = (x_grid - px) ** 2 + (y_grid - py) ** 2 <= radius_px ** 2
    canvas[mask] = color


def _world_to_pixel(world_position: tuple[float, float]) -> tuple[int, int]:
    x, y = world_position
    px = int(np.interp(x, [-10.0, 10.0], [40, CANVAS_WIDTH - 40]))
    py = int(np.interp(y, [-4.0, 14.0], [CANVAS_HEIGHT - 40, 40]))
    return px, py
