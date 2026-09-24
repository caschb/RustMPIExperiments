"""Rank ownership drawn as tiles, with the particles that changed owner marked.

The eight-neighbour halo schematic on the communication slide says what the
exchange is; this says what it is exchanging and why.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import patheffects
from matplotlib.patches import Rectangle

from . import palette, pic


def _draw_tiles(ax, tiles):
    for _, tile in tiles.iterrows():
        ax.add_patch(
            Rectangle(
                (tile["left"], tile["bottom"]),
                tile["right"] - tile["left"],
                tile["top"] - tile["bottom"],
                fill=False,
                edgecolor=palette.INK,
                lw=0.8,
                zorder=4,
            )
        )
        label = ax.text(
            (tile["left"] + tile["right"]) / 2,
            tile["top"] - (tile["top"] - tile["bottom"]) * 0.07,
            f"rank {int(tile['rank'])}",
            ha="center",
            va="top",
            fontsize=6.5,
            color="#5a5a5a",
            zorder=5,
        )
        # The labels sit on top of the particles, so give them a halo.
        label.set_path_effects(
            [patheffects.withStroke(linewidth=1.8, foreground="white")]
        )


def plot(
    data_dir: Path,
    out_path: Path,
    prefix: str = "p",
    first_step: int = 0,
    last_step: int | None = None,
    mark_since: int | None = None,
    grid_size: float = 1000.0,
    width: float = 6.6,
    height: float = 3.6,
) -> Path:
    palette.apply_style()

    frame = pic.load_particle_dump(data_dir, prefix)
    tiles = pic.load_tiles(data_dir, prefix).sort_values("rank")

    steps = sorted(frame["step"].unique())
    if last_step is None:
        # The final record is written after the loop, one step past the rest.
        last_step = int(steps[-2]) if len(steps) > 2 else int(steps[-1])

    if mark_since is None:
        # Default to the step immediately before, so the ringed particles are
        # exactly the ones that step's halo exchange had to send.
        earlier = [s for s in steps if s < last_step]
        mark_since = int(earlier[-1]) if earlier else int(first_step)

    start = frame[frame["step"] == first_step].set_index("id")
    end = frame[frame["step"] == last_step].set_index("id")
    previous = frame[frame["step"] == mark_since].set_index("id")
    shared = start.index.intersection(end.index)
    start, end = start.loc[shared], end.loc[shared]
    common = end.index.intersection(previous.index)
    moved = (
        (end.loc[common, "rank"] != previous.loc[common, "rank"])
        .reindex(end.index, fill_value=False)
        .to_numpy()
    )

    n_x = tiles["left"].nunique()
    n_y = tiles["bottom"].nunique()

    fig, axes = plt.subplots(1, 2, figsize=(width, height), sharex=True, sharey=True)
    for ax, (label, snapshot) in zip(
        axes,
        [(f"step {first_step}", start), (f"step {last_step}", end)],
        strict=True,
    ):
        _draw_tiles(ax, tiles)
        colours = [
            palette.RANK_COLOURS[int(r) % len(palette.RANK_COLOURS)]
            for r in snapshot["rank"]
        ]
        ax.scatter(
            snapshot["x"], snapshot["y"], s=5, c=colours, linewidths=0, zorder=2
        )
        ax.set_xlim(0, grid_size)
        ax.set_ylim(0, grid_size)
        ax.set_aspect("equal")
        ax.set_xlabel("$x$ [cells]")
        ax.set_title(label, fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)

    # Ring the particles now owned by a different rank than they started on.
    axes[1].scatter(
        end["x"][moved],
        end["y"][moved],
        s=46,
        facecolors="none",
        edgecolors=palette.RED,
        linewidths=1.0,
        zorder=3,
    )
    axes[0].set_ylabel("$y$ [cells]")

    fig.text(
        0.5,
        -0.03,
        f"{len(shared)} particles over {n_x}x{n_y} rank tiles. "
        f"{int(moved.sum())} changed owner during step {last_step} "
        f"({100 * moved.mean():.1f}%), ringed on the right.",
        ha="center",
        fontsize=7,
        color="#6a6a6a",
    )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path
