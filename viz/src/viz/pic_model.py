"""What the PIC kernel actually simulates.

Left: the fixed charge mesh and the four charges one particle feels, with the
forces computed from the same expression the codes use. Right: particle tracks
over the mesh, against the closed form the PRK initialization is built to give.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

from . import palette, pic

Q = 1.0


def mesh_charge(column: int) -> float:
    """Charge at a mesh point. The mesh alternates sign by column only."""
    return Q if column % 2 == 0 else -Q


def coulomb(x_dist: float, y_dist: float, q1: float, q2: float):
    """Force on the particle from one mesh charge, as in compute_coulomb."""
    r2 = x_dist**2 + y_dist**2
    r = np.sqrt(r2)
    magnitude = q1 * q2 / r2
    return magnitude * x_dist / r, magnitude * y_dist / r


def _stencil_panel(ax, particle=(3.35, 2.4), cols=8, rows=5, q_particle=Q):
    cell_x, cell_y = int(np.floor(particle[0])), int(np.floor(particle[1]))
    rel_x, rel_y = particle[0] - cell_x, particle[1] - cell_y

    for x in range(cols + 1):
        ax.axvline(x, color=palette.GREY, lw=0.5, zorder=0)
    for y in range(rows + 1):
        ax.axhline(y, color=palette.GREY, lw=0.5, zorder=0)

    ax.add_patch(
        Rectangle(
            (cell_x, cell_y), 1, 1,
            facecolor=palette.GREY, alpha=0.5, edgecolor="none", zorder=0,
        )
    )
    ax.text(
        cell_x + 0.5, cell_y - 0.16, "the cell holding the particle",
        ha="center", va="top", fontsize=6.8, color="#8c8c8c",
    )

    corners = [
        (cell_x, cell_y, rel_x, rel_y),
        (cell_x + 1, cell_y, rel_x - 1.0, rel_y),
        (cell_x, cell_y + 1, rel_x, rel_y - 1.0),
        (cell_x + 1, cell_y + 1, rel_x - 1.0, rel_y - 1.0),
    ]
    stencil = {(c[0], c[1]) for c in corners}

    for x in range(cols + 1):
        for y in range(rows + 1):
            charge = mesh_charge(x)
            ax.scatter(
                x,
                y,
                s=44 if (x, y) in stencil else 22,
                marker="o" if charge > 0 else "s",
                color=palette.NAVY if charge > 0 else palette.RED,
                zorder=2,
                linewidths=1.1 if (x, y) in stencil else 0,
                edgecolors=palette.INK if (x, y) in stencil else "none",
            )

    total = np.zeros(2)
    for cx, cy, dx, dy in corners:
        # The displacement runs from the mesh charge to the particle, so a
        # like-signed pair pushes the particle away from that charge.
        fx, fy = coulomb(dx, dy, q_particle, mesh_charge(cx))
        total += (fx, fy)
        ax.annotate(
            "",
            xy=(particle[0] + fx * 0.34, particle[1] + fy * 0.34),
            xytext=particle,
            arrowprops={"arrowstyle": "->", "color": "#6f6f6f", "lw": 1.1},
            zorder=3,
        )
        ax.plot([cx, particle[0]], [cy, particle[1]], color=palette.GREY, lw=0.6, zorder=1)

    ax.annotate(
        "",
        xy=(particle[0] + total[0] * 0.34, particle[1] + total[1] * 0.34),
        xytext=particle,
        arrowprops={"arrowstyle": "-|>", "color": palette.INK, "lw": 1.6},
        zorder=4,
    )
    ax.scatter(*particle, s=34, color=palette.YELLOW, edgecolors=palette.INK,
               linewidths=0.8, zorder=5)

    ax.set_xlim(cell_x - 2.6, cell_x + 3.6)
    ax.set_ylim(cell_y - 3.5, cell_y + 2.6)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("the four mesh charges one particle feels", fontsize=8.5)

    handles = [
        plt.Line2D([], [], ls="", marker="o", color=palette.NAVY, label="$+Q$ mesh charge"),
        plt.Line2D([], [], ls="", marker="s", color=palette.RED, label="$-Q$ mesh charge"),
        plt.Line2D([], [], ls="", marker="o", color=palette.YELLOW,
                   markeredgecolor=palette.INK, label="particle"),
        plt.Line2D([], [], color=palette.INK, lw=1.6, label="resultant force"),
    ]
    ax.legend(handles=handles, loc="lower center", ncol=2, fontsize=6.8,
              bbox_to_anchor=(0.5, 0.0), handletextpad=0.5, columnspacing=1.2)


def _split_on_wrap(values: np.ndarray, grid_size: float) -> list[slice]:
    """Break a track where a periodic wrap makes a segment meaningless."""
    jumps = np.flatnonzero(np.abs(np.diff(values)) > grid_size / 2.0)
    edges = [0, *(int(j) + 1 for j in jumps), len(values)]
    return [slice(a, b) for a, b in zip(edges, edges[1:]) if b - a > 1]


def _tracks_panel(ax, data_dir: Path, grid_size: float, n_lines: int, prefix: str):
    frame = pic.load_particle_dump(data_dir, prefix)
    frame = frame.sort_values(["id", "step"])

    mesh = np.arange(0, grid_size + 1)
    xs, ys = np.meshgrid(mesh, mesh)
    signs = np.where(xs % 2 == 0, 1, -1)
    ax.scatter(xs[signs > 0], ys[signs > 0], s=1.4, color=palette.NAVY, alpha=0.30, linewidths=0)
    ax.scatter(xs[signs < 0], ys[signs < 0], s=1.4, color=palette.RED, alpha=0.30, linewidths=0)

    chosen = sorted(frame["id"].unique())[:n_lines]
    for index, particle_id in enumerate(chosen):
        track = frame[frame["id"] == particle_id]
        x = track["x"].to_numpy()
        y = track["y"].to_numpy()
        colour = palette.RANK_COLOURS[index % len(palette.RANK_COLOURS)]
        for piece in _split_on_wrap(x, grid_size):
            for sub in _split_on_wrap(y[piece], grid_size):
                ax.plot(x[piece][sub], y[piece][sub], color=colour, lw=1.0, zorder=2)
        ax.scatter(x, y, s=9, color=colour, zorder=3, linewidths=0)
        ax.scatter(x[:1], y[:1], s=30, facecolors="white", edgecolors=colour,
                   linewidths=1.1, zorder=4)

    ax.set_xlim(0, grid_size)
    ax.set_ylim(0, grid_size)
    ax.set_aspect("equal")
    ax.set_xlabel("$x$ [cells]")
    ax.set_ylabel("$y$ [cells]")
    ax.set_title(
        f"{len(chosen)} particle tracks, {int(frame['step'].max())} steps",
        fontsize=8.5,
    )
    ax.spines[["top", "right"]].set_visible(False)


def plot(
    data_dir: Path,
    out_path: Path,
    grid_size: float = 24.0,
    n_lines: int = 5,
    prefix: str = "t",
    width: float = 6.6,
    height: float = 3.1,
) -> Path:
    palette.apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(width, height))
    _stencil_panel(axes[0])
    _tracks_panel(axes[1], data_dir, grid_size, n_lines, prefix)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path
