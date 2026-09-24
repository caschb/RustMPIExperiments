"""Loading of BS-SOLCTRA inputs and of the diagnostics the Rust code writes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# Geometry constants, mirroring bs-solctra-mpi-rs/src/constants.rs.
MAJOR_RADIUS = 0.2381
MINOR_RADIUS = 0.0944165


def load_coils(resource_dir: Path) -> list[np.ndarray]:
    """Return each modular coil as an (n, 3) array of points.

    The files store a closed loop with the first point repeated at the end.
    """
    files = sorted(Path(resource_dir).glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No coil files in {resource_dir}")
    return [pd.read_csv(f)[["x", "y", "z"]].to_numpy() for f in files]


def _concat_ranks(data_dir: Path, stem: str) -> pd.DataFrame:
    files = sorted(Path(data_dir).glob(f"{stem}_*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No {stem}_*.csv in {data_dir}. Run the simulation with --diagnostics first."
        )
    frames = [pd.read_csv(f) for f in files]
    return pd.concat(frames, ignore_index=True)


def load_summaries(data_dir: Path) -> pd.DataFrame:
    """One row per traced field line, sorted by starting radius."""
    df = _concat_ranks(data_dir, "fieldlines")
    df["start_R"] = np.hypot(df["start_x"], df["start_y"])
    df["confined"] = df["lost_at_step"] < 0
    return df.sort_values("start_R").reset_index(drop=True)


def load_punctures(data_dir: Path) -> pd.DataFrame:
    return _concat_ranks(data_dir, "poincare")


def load_trajectories(data_dir: Path) -> pd.DataFrame:
    return _concat_ranks(data_dir, "trajectory").sort_values(["line_id", "step"])


@dataclass
class Trajectory:
    line_id: int
    points: np.ndarray  # (n, 3)
    b_magnitude: np.ndarray  # (n,)


def split_trajectories(df: pd.DataFrame, min_points: int = 2) -> list[Trajectory]:
    out = []
    for line_id, group in df.groupby("line_id", sort=True):
        if len(group) < min_points:
            continue
        out.append(
            Trajectory(
                line_id=int(line_id),
                points=group[["x", "y", "z"]].to_numpy(),
                b_magnitude=group["b_magnitude"].to_numpy(),
            )
        )
    return out


def write_radial_starts(path: Path, count: int, r_min: float, r_max: float) -> Path:
    """Write starting points along the outboard midplane at phi = 0.

    The particles file shipped with the code is a grid over eleven toroidal
    angles, which is right for a scaling benchmark but scatters the field lines
    for a Poincare section. A radial ray at the section plane gives one line per
    flux surface instead.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    radii = np.linspace(r_min, r_max, count)
    frame = pd.DataFrame({"x": radii, "y": 0.0, "z": 0.0})
    frame.to_csv(path, index=False)
    return path
