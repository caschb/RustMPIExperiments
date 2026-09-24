"""The PRK analytical check, for C and Rust together.

The deck states that both versions pass it. They do more than pass: over every
sampled step of every initialization style the simulated position equals the
closed form in every bit, in both languages, so the residual panel is a line on
zero inside a band drawn at the tolerance the check actually applies.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import palette, pic

IMPLEMENTATIONS = [("C", palette.C_LANG), ("Rust", palette.RUST)]


def _load_all_styles(data_dir: Path, implementation: str, styles: list[str]) -> pd.DataFrame:
    frames = []
    for style in styles:
        frame = pic.load_particle_dump(data_dir, f"{implementation}-{style}")
        frame["style"] = style
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def _deviation(frame: pd.DataFrame, grid_size: float) -> pd.Series:
    x, y = pic.analytic_position(frame, grid_size)
    return np.maximum((frame["x"] - x).abs(), (frame["y"] - y).abs())


def _split_on_wrap(values: np.ndarray, grid_size: float) -> list[slice]:
    jumps = np.flatnonzero(np.abs(np.diff(values)) > grid_size / 2.0)
    edges = [0, *(int(j) + 1 for j in jumps), len(values)]
    return [slice(a, b) for a, b in zip(edges, edges[1:]) if b - a > 1]


def plot(
    data_dir: Path,
    out_path: Path,
    grid_size: float = 200.0,
    styles: list[str] | None = None,
    track_style: str = "geometric",
    n_tracks: int = 3,
    width: float = 6.6,
    height: float = 2.9,
) -> Path:
    palette.apply_style()
    styles = styles or ["geometric", "sinusoidal", "linear", "patch"]

    loaded = {
        name: _load_all_styles(data_dir, name.lower(), styles)
        for name, _ in IMPLEMENTATIONS
    }

    fig, axes = plt.subplots(1, 2, figsize=(width, height))

    # Left: a few trajectories, closed form as the line, both codes as markers.
    reference = loaded["Rust"]
    reference = reference[reference["style"] == track_style].sort_values(["id", "step"])
    ids = reference["id"].unique()
    chosen = [ids[i * len(ids) // n_tracks] for i in range(n_tracks)]

    for index, particle_id in enumerate(chosen):
        track = reference[reference["id"] == particle_id]
        analytic_x, _ = pic.analytic_position(track, grid_size)
        steps = track["step"].to_numpy()
        values = analytic_x.to_numpy()
        colour = palette.RANK_COLOURS[(index * 3) % len(palette.RANK_COLOURS)]
        for piece in _split_on_wrap(values, grid_size):
            ax_label = "closed form" if index == 0 and piece.start == 0 else None
            axes[0].plot(
                steps[piece], values[piece], color=colour, lw=1.2, alpha=0.7,
                zorder=1, label=ax_label,
            )

    for name, colour in IMPLEMENTATIONS:
        subset = loaded[name]
        subset = subset[(subset["style"] == track_style) & subset["id"].isin(chosen)]
        if name == "C":
            axes[0].scatter(
                subset["step"], subset["x"], s=17, marker="o", facecolors="none",
                edgecolors=colour, linewidths=0.8, label=name, zorder=3,
            )
        else:
            axes[0].scatter(
                subset["step"], subset["x"], s=9, marker="x", color=colour,
                linewidths=0.8, label=name, zorder=4,
            )

    axes[0].set_xlabel("timestep")
    axes[0].set_ylabel("$x$ [cells]")
    axes[0].set_title(f"{len(chosen)} trajectories, {track_style}", fontsize=8.5)
    # Headroom above the data, so the legend does not sit on the tracks.
    axes[0].set_ylim(-0.04 * grid_size, 1.34 * grid_size)
    axes[0].legend(loc="upper center", ncol=3, fontsize=7)
    axes[0].spines[["top", "right"]].set_visible(False)

    # Right: how far either implementation ever gets from the closed form.
    axes[1].axhspan(
        -pic.VERIFY_TOLERANCE, pic.VERIFY_TOLERANCE,
        color=palette.GREY, alpha=0.55, zorder=0,
    )

    worst = 0.0
    total = 0
    for name, colour in IMPLEMENTATIONS:
        frame = loaded[name]
        errors = _deviation(frame, grid_size)
        by_step = pd.DataFrame({"step": frame["step"], "error": errors}).groupby(
            "step", as_index=False
        )["error"].max()
        worst = max(worst, float(by_step["error"].max()))
        total += len(errors)
        axes[1].plot(
            by_step["step"], by_step["error"], color=colour,
            lw=2.0 if name == "C" else 1.0,
            ls="-" if name == "C" else "--",
            label=name, zorder=2,
        )

    axes[1].set_ylim(-2.2 * pic.VERIFY_TOLERANCE, 2.2 * pic.VERIFY_TOLERANCE)
    axes[1].set_xlabel("timestep")
    axes[1].set_ylabel("deviation [cells]")
    axes[1].set_title("distance from the closed form", fontsize=8.5)
    axes[1].legend(loc="upper right", fontsize=7.5)
    axes[1].spines[["top", "right"]].set_visible(False)
    axes[1].text(
        0.03, 0.90,
        f"PRK tolerance $\\pm${pic.VERIFY_TOLERANCE:g}",
        transform=axes[1].transAxes, fontsize=7, color="#6a6a6a", va="top",
    )
    axes[1].text(
        0.03, 0.07,
        f"worst of {total:,} samples across {len(styles)} styles: {worst:g}".replace(",", " "),
        transform=axes[1].transAxes, fontsize=7, color=palette.INK, va="bottom",
    )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path
