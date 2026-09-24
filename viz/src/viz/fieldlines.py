"""3D view of the SCR-1 coil set with traced field lines running through it."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pyvista as pv

from . import data, palette


def _polyline(points: np.ndarray) -> pv.PolyData:
    """A PolyData holding one connected polyline through `points`."""
    n = len(points)
    mesh = pv.PolyData()
    mesh.points = points
    mesh.lines = np.hstack([[n], np.arange(n)]).astype(np.int32)
    return mesh


def _camera_position(azimuth: float, elevation: float, distance: float):
    az = math.radians(azimuth)
    el = math.radians(elevation)
    return [
        (
            distance * math.cos(el) * math.cos(az),
            distance * math.cos(el) * math.sin(az),
            distance * math.sin(el),
        ),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
    ]


def _select_coils(coils: list[np.ndarray], fraction: float, azimuth: float):
    """Keep a contiguous arc of coils, dropping the ones nearest the camera.

    Twelve closed coils hide most of the interior from any angle, so the
    cutaway is what makes the field lines readable.
    """
    if fraction >= 1.0:
        return coils
    angles = np.array(
        [math.atan2(c[:, 1].mean(), c[:, 0].mean()) for c in coils]
    )
    # Angular distance from the camera direction; the far coils are kept.
    delta = np.abs(np.angle(np.exp(1j * (angles - math.radians(azimuth)))))
    keep = np.argsort(-delta)[: max(1, int(round(len(coils) * fraction)))]
    return [coils[i] for i in sorted(keep)]



def _save_trimmed(image: np.ndarray, out_path: Path, margin: int = 24) -> None:
    """Crop the uniform border off a render before saving.

    The camera is placed from spherical angles rather than fitted to the scene,
    so the framing is predictable but rarely tight. Trimming afterwards keeps
    every view tight without hand-tuning zoom per figure.
    """
    from matplotlib import image as mpimg

    background = image[0, 0]
    content = np.any(image != background, axis=-1)
    rows = np.flatnonzero(content.any(axis=1))
    cols = np.flatnonzero(content.any(axis=0))
    if rows.size and cols.size:
        top = max(int(rows[0]) - margin, 0)
        bottom = min(int(rows[-1]) + margin + 1, image.shape[0])
        left = max(int(cols[0]) - margin, 0)
        right = min(int(cols[-1]) + margin + 1, image.shape[1])
        image = image[top:bottom, left:right]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mpimg.imsave(str(out_path), image)


def render(
    data_dir: Path,
    resource_dir: Path,
    out_path: Path,
    *,
    colour_by: str = "field",
    max_step: int | None = None,
    max_lines: int | None = None,
    line_ids: list[int] | None = None,
    coil_fraction: float = 1.0,
    coil_opacity: float = 1.0,
    coil_radius: float = 0.0018,
    line_radius: float = 0.0016,
    window_size: tuple[int, int] = (2200, 1500),
    azimuth: float = 55.0,
    elevation: float = 22.0,
    distance: float = 1.15,
    zoom: float = 1.0,
    background: str = "white",
    show_scalar_bar: bool = True,
) -> Path:
    """Render the coils and field lines to an image.

    `colour_by` is "field" for the magnetic field magnitude along each line, or
    "radius" for one colour per line taken from its starting minor radius.
    `max_step` trims each trajectory and `line_ids` selects a subset, so one
    long trace can serve both a few-turn overview and a many-turn plot of the
    surfaces a handful of lines sweep out.
    """
    frame = data.load_trajectories(data_dir)
    if max_step is not None:
        frame = frame[frame["step"] <= max_step]
    if line_ids is not None:
        frame = frame[frame["line_id"].isin(line_ids)]
    trajectories = data.split_trajectories(frame)
    if max_lines is not None:
        trajectories = trajectories[:max_lines]
    if not trajectories:
        raise ValueError(f"No usable trajectories in {data_dir}")

    summaries = data.load_summaries(data_dir)
    radius_of = dict(
        zip(summaries["line_id"], summaries["start_radius_normalised"], strict=True)
    )

    pv.set_plot_theme("document")
    plotter = pv.Plotter(off_screen=True, window_size=list(window_size))
    plotter.set_background(background)

    coils = _select_coils(data.load_coils(resource_dir), coil_fraction, azimuth)
    for coil in coils:
        tube = _polyline(coil).tube(radius=coil_radius, n_sides=16)
        plotter.add_mesh(
            tube,
            color="#8c8c8c",
            opacity=coil_opacity,
            smooth_shading=True,
            specular=0.4,
            specular_power=30,
        )

    cmap = palette.radius_colormap()
    clim = None
    if colour_by == "field":
        # One scale across all lines, so colour means the same thing everywhere.
        all_b = np.concatenate([t.b_magnitude for t in trajectories])
        clim = (float(all_b.min()), float(all_b.max()))

    for index, traj in enumerate(trajectories):
        mesh = _polyline(traj.points)
        if colour_by == "field":
            mesh["|B| [T]"] = traj.b_magnitude
            tube = mesh.tube(radius=line_radius, n_sides=14)
            plotter.add_mesh(
                tube,
                scalars="|B| [T]",
                cmap="viridis",
                clim=clim,
                smooth_shading=True,
                show_scalar_bar=show_scalar_bar and index == 0,
                scalar_bar_args={
                    "title": "|B|  [T]",
                    "vertical": True,
                    "position_x": 0.855,
                    "position_y": 0.28,
                    "height": 0.46,
                    "width": 0.035,
                    "n_labels": 5,
                    "fmt": "%.3f",
                    "title_font_size": 30,
                    "label_font_size": 26,
                    "color": palette.INK,
                },
            )
        else:
            normalised = min(radius_of.get(traj.line_id, 0.0), 1.0)
            tube = mesh.tube(radius=line_radius, n_sides=14)
            plotter.add_mesh(tube, color=cmap(normalised)[:3], smooth_shading=True)

    plotter.enable_anti_aliasing("ssaa")
    plotter.camera_position = _camera_position(azimuth, elevation, distance)
    plotter.camera.zoom(zoom)

    image = plotter.screenshot(return_img=True)
    plotter.close()

    out_path = Path(out_path)
    _save_trimmed(image, out_path)
    return out_path
