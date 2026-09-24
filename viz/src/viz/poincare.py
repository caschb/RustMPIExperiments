"""Poincaré section: where each field line pierces a fixed toroidal plane.

Closed nested curves are intact flux surfaces, which is what confinement in a
stellarator means. Scatter without structure is a chaotic region.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from . import data, palette


def plot(
    data_dir: Path,
    out_path: Path,
    phi_label: str = r"$\varphi = 0$",
    show_boundary: bool = False,
    point_size: float = 1.1,
    width: float = 4.2,
    height: float = 3.4,
) -> Path:
    """Draw the section.

    `show_boundary` adds the circle the code uses as its containment test. It is
    a good deal larger than the surfaces that actually close, so including it
    shrinks the plasma to a quarter of the frame; it is off by default and worth
    turning on only when that gap is the point being made.
    """
    palette.apply_style()

    punctures = data.load_punctures(data_dir)
    summaries = data.load_summaries(data_dir)
    radius_of = dict(
        zip(summaries["line_id"], summaries["start_radius_normalised"], strict=True)
    )

    # Normalise the colour ramp over the radii actually traced, not over the
    # nominal 0..1, so the full ramp is used however the scan was set up.
    drawn_radii = [
        radius_of[line_id]
        for line_id, group in punctures.groupby("line_id")
        if line_id in radius_of and len(group) >= 2
    ]
    r_min, r_max = min(drawn_radii), max(drawn_radii)
    norm = plt.Normalize(r_min, r_max)
    cmap = palette.radius_colormap()

    fig, ax = plt.subplots(figsize=(width, height))

    if show_boundary:
        theta = np.linspace(0, 2 * np.pi, 400)
        ax.plot(
            data.MAJOR_RADIUS + data.MINOR_RADIUS * np.cos(theta),
            data.MINOR_RADIUS * np.sin(theta),
            color=palette.GREY,
            lw=1.0,
            zorder=0,
        )
        ax.text(
            data.MAJOR_RADIUS,
            data.MINOR_RADIUS * 1.03,
            "containment boundary",
            color="#9a9a9a",
            fontsize=7,
            ha="center",
            va="bottom",
        )

    drawn = 0
    for line_id, group in punctures.groupby("line_id", sort=True):
        normalised = radius_of.get(line_id)
        if normalised is None or len(group) < 2:
            continue
        ax.scatter(
            group["r"],
            group["z"],
            s=point_size,
            linewidths=0,
            color=cmap(norm(normalised)),
            rasterized=True,
        )
        drawn += 1

    if not show_boundary:
        pad = 0.12 * max(
            punctures["r"].max() - punctures["r"].min(),
            punctures["z"].max() - punctures["z"].min(),
        )
        ax.set_xlim(punctures["r"].min() - pad, punctures["r"].max() + pad)
        ax.set_ylim(punctures["z"].min() - pad, punctures["z"].max() + pad)

    ax.set_aspect("equal")
    ax.set_xlabel(r"$R$ [m]")
    ax.set_ylabel(r"$z$ [m]")
    ax.set_title(f"Poincaré section at {phi_label}", pad=8)
    ax.spines[["top", "right"]].set_visible(False)

    mappable = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    bar = fig.colorbar(mappable, ax=ax, fraction=0.045, pad=0.03)
    bar.set_label("starting minor radius $r/a$")
    bar.outline.set_visible(False)

    ax.text(
        0.02,
        0.02,
        f"{drawn} field lines, {len(punctures):,} plane crossings".replace(",", " "),
        transform=ax.transAxes,
        fontsize=7,
        color="#6a6a6a",
        va="bottom",
    )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def plot_confinement(
    data_dir: Path,
    out_path: Path,
    step_size: float,
    width: float = 4.4,
    height: float = 2.8,
) -> Path:
    """Arc length each line survives against where it started.

    The companion to the section: the same edge as a hard cutoff in one scalar,
    which is easier to read from the back of a room.
    """
    palette.apply_style()
    summaries = data.load_summaries(data_dir)

    traced = (
        np.where(
            summaries["confined"],
            summaries["steps_traced"],
            summaries["lost_at_step"],
        ).astype(float)
        * step_size
    )

    fig, ax = plt.subplots(figsize=(width, height))
    confined = summaries["confined"].to_numpy()
    ax.scatter(
        summaries["start_R"][confined],
        traced[confined],
        s=16,
        color=palette.NAVY,
        label="confined for the whole trace",
    )
    ax.scatter(
        summaries["start_R"][~confined],
        traced[~confined],
        s=22,
        color=palette.RED,
        marker="x",
        linewidths=1.1,
        label="left the containment region",
    )

    ax.set_xlabel(r"starting $R$ [m]")
    ax.set_ylabel("traced arc length [m]")
    ax.set_yscale("log")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="lower center")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path
