"""Loader utilities for the public ANavS warehouse LiDAR dataset."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np


@dataclass(frozen=True)
class BoundingBox3D:
    class_name: str
    position_x_m: float
    position_y_m: float
    position_z_m: float
    scale_x_m: float
    scale_y_m: float
    scale_z_m: float
    yaw_angle_rad: float

    @property
    def center_xy(self) -> np.ndarray:
        return np.array([self.position_x_m, self.position_y_m], dtype=np.float32)

    @property
    def radial_distance_m(self) -> float:
        return float(np.linalg.norm(self.center_xy))

    @property
    def volume_m3(self) -> float:
        return float(max(self.scale_x_m, 0.0) * max(self.scale_y_m, 0.0) * max(self.scale_z_m, 0.0))


@dataclass(frozen=True)
class WarehouseScanRecord:
    scan_id: str
    frame_index: int
    sequence_id: str
    scan_chunk: str
    points_xyz: np.ndarray
    intensity: np.ndarray | None
    boxes: list[BoundingBox3D]
    bin_path: Path
    label_path: Path


def _read_bin_points(path: Path) -> tuple[np.ndarray, np.ndarray | None]:
    raw = np.fromfile(path, dtype=np.float32)
    if raw.size == 0:
        return np.empty((0, 3), dtype=np.float32), None
    if raw.size % 4 == 0:
        reshaped = raw.reshape(-1, 4)
        return reshaped[:, :3], reshaped[:, 3]
    if raw.size % 3 == 0:
        reshaped = raw.reshape(-1, 3)
        return reshaped, None
    raise ValueError(f"Unsupported point cloud shape in {path}")


def _read_labels(path: Path) -> list[BoundingBox3D]:
    boxes: list[BoundingBox3D] = []
    if not path.exists():
        return boxes
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) != 8:
            continue
        boxes.append(
            BoundingBox3D(
                class_name=parts[0],
                position_x_m=float(parts[1]),
                position_y_m=float(parts[2]),
                position_z_m=float(parts[3]),
                scale_x_m=float(parts[4]),
                scale_y_m=float(parts[5]),
                scale_z_m=float(parts[6]),
                yaw_angle_rad=float(parts[7]),
            )
        )
    return boxes


def iter_dataset_records(
    dataset_root: str | Path,
    chunk_size: int = 50,
    limit: int | None = None,
    sequence_id: str = "warehouse_main",
) -> Iterator[WarehouseScanRecord]:
    root = Path(dataset_root)
    bin_dir = root / "bin"
    label_dir = root / "label"
    bin_files = sorted(bin_dir.glob("*.bin"))
    if limit is not None:
        bin_files = bin_files[:limit]
    for frame_index, bin_path in enumerate(bin_files):
        scan_id = bin_path.stem
        label_path = label_dir / f"{scan_id}.txt"
        points_xyz, intensity = _read_bin_points(bin_path)
        boxes = _read_labels(label_path)
        yield WarehouseScanRecord(
            scan_id=scan_id,
            frame_index=frame_index,
            sequence_id=sequence_id,
            scan_chunk=f"{sequence_id}_chunk_{frame_index // max(chunk_size, 1):04d}",
            points_xyz=points_xyz,
            intensity=intensity,
            boxes=boxes,
            bin_path=bin_path,
            label_path=label_path,
        )

