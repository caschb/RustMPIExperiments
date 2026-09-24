"""PIC particle migration: the communication volume behind the MAPE table.

The deck orders the four initialization styles by communication volume and
attributes the Rust-versus-C gap to it, but that ordering was never measured.
These figures measure it.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import palette

STYLES = ["geometric", "sinusoidal", "linear", "patch"]

STYLE_LABEL = {
    "geometric": "Geometric",
    "sinusoidal": "Sinusoidal",
    "linear": "Linear",
    "patch": "Patch",
}

# Linear is the outlier the argument turns on, so it gets the accent colour.
STYLE_COLOUR = {
    "geometric": palette.NAVY,
    "sinusoidal": palette.BLUE,
    "linear": palette.RED,
    "patch": palette.GREEN,
}

# Mean absolute percentage error of the Rust rate against the C baseline, as
# reported in the paper and the deck. Not derivable from anything local: these
# come from the Kabré runs.
MAPE = {
    ("strong", "geometric"): 10.59,
    ("strong", "linear"): 12.65,
    ("strong", "patch"): 7.45,
    ("strong", "sinusoidal"): 8.33,
    ("weak", "geometric"): 4.32,
    ("weak", "linear"): 30.90,
    ("weak", "patch"): 8.59,
    ("weak", "sinusoidal"): 13.82,
}


# The tolerance verify_particle applies, as EPSILON in the source of both codes.
VERIFY_TOLERANCE = 1e-6


def load_particle_dump(root: Path, prefix: str = "p") -> pd.DataFrame:
    """Read every <prefix>_<rank>.csv written by --particle-dump."""
    files = [
        path
        for path in sorted(Path(root).glob(f"{prefix}_*.csv"))
        if "_tiles_" not in path.name
    ]
    if not files:
        raise FileNotFoundError(f"No {prefix}_<rank>.csv under {root}")
    return pd.concat([pd.read_csv(path) for path in files], ignore_index=True)


def load_tiles(root: Path, prefix: str = "p") -> pd.DataFrame:
    """Read the per-rank tile bounds written alongside a particle dump."""
    files = sorted(Path(root).glob(f"{prefix}_tiles_*.csv"))
    if not files:
        raise FileNotFoundError(f"No {prefix}_tiles_<rank>.csv under {root}")
    return pd.concat([pd.read_csv(path) for path in files], ignore_index=True)


def analytic_position(frame: pd.DataFrame, grid_size: float):
    """The closed-form position the PRK initialization is built to produce.

    Each particle travels at a constant (2k+1, m) cells per step on a periodic
    domain; this is what verify_particle checks against.
    """
    steps = frame["step"]
    x = (frame["x0"] + steps * (2.0 * frame["k"] + 1.0)) % grid_size
    y = (frame["y0"] + steps * frame["m"]) % grid_size
    return x, y


def load_migration(root: Path) -> pd.DataFrame:
    """Read every mig_<rank>.csv under <root>/<scaling>/<style>/r<ranks>/."""
    frames = []
    for path in sorted(Path(root).glob("*/*/r*/mig_*.csv")):
        frame = pd.read_csv(path)
        frame["scaling"] = path.parts[-4]
        frame["style"] = path.parts[-3]
        frame["ranks"] = int(path.parts[-2].lstrip("r"))
        frames.append(frame)
    if not frames:
        raise FileNotFoundError(f"No migration logs under {root}. Run sweep_pic.sh first.")
    return pd.concat(frames, ignore_index=True)


def per_step_totals(frame: pd.DataFrame) -> pd.DataFrame:
    """Particles migrated per step, summed over the ranks of a configuration.

    Step 0 is dropped: the PIC timer starts at step 1, and the first step also
    carries the initial placement's migration rather than the steady state.
    """
    moving = frame[frame["step"] > 0]
    return moving.groupby(
        ["scaling", "style", "ranks", "step"], as_index=False
    )["migrated"].sum()


def mean_migration(
    frame: pd.DataFrame, node_counts: list[int] | None = None, per_rank: bool = False
) -> pd.DataFrame:
    """Mean particles migrated per step for each (scaling, style).

    Averaged first over steps within a rank count, then over rank counts, so
    each configuration carries the same weight the MAPE gives it.
    """
    totals = per_step_totals(frame)
    if node_counts is not None:
        totals = totals[totals["ranks"].isin(node_counts)]
    if per_rank:
        totals = totals.assign(migrated=totals["migrated"] / totals["ranks"])
    per_config = totals.groupby(
        ["scaling", "style", "ranks"], as_index=False
    )["migrated"].mean()
    return per_config.groupby(["scaling", "style"], as_index=False)["migrated"].mean()


def plot_per_step(
    data_dir: Path,
    out_path: Path,
    ranks: int = 8,
    width: float = 6.4,
    height: float = 2.7,
) -> Path:
    """Migration against timestep, one panel per scaling mode."""
    palette.apply_style()
    totals = per_step_totals(load_migration(data_dir))
    totals = totals[totals["ranks"] == ranks]
    if totals.empty:
        raise ValueError(f"No data at {ranks} ranks in {data_dir}")

    fig, axes = plt.subplots(1, 2, figsize=(width, height), sharey=True)
    for ax, scaling in zip(axes, ["strong", "weak"], strict=True):
        subset = totals[totals["scaling"] == scaling]
        for style in STYLES:
            series = subset[subset["style"] == style].sort_values("step")
            if series.empty:
                continue
            ax.plot(
                series["step"],
                series["migrated"],
                color=STYLE_COLOUR[style],
                lw=1.3,
                label=STYLE_LABEL[style],
            )
        ax.set_title(f"{scaling} scaling", fontsize=9)
        ax.set_xlabel("timestep")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("particles migrated\nper step")
    axes[1].legend(loc="center right", fontsize=7.5)
    axes[0].annotate(
        "Patch: every particle on rank 0\nuntil the block crosses a tile edge",
        xy=(72, 0),
        xytext=(18, 2600),
        fontsize=7,
        color=STYLE_COLOUR["patch"],
        arrowprops={"arrowstyle": "-", "color": STYLE_COLOUR["patch"], "lw": 0.7},
    )

    fig.text(
        0.5,
        -0.06,
        f"{ranks} ranks, grid 1000, summed over all ranks and all eight neighbours",
        ha="center",
        fontsize=7,
        color="#6a6a6a",
    )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def plot_migration_vs_mape(
    data_dir: Path,
    out_path: Path,
    node_counts: list[int] | None = None,
    per_rank: bool = False,
    width: float = 5.2,
    height: float = 3.6,
) -> Path:
    """The eight (style, scaling) points: communication volume against MAPE.

    This figure tests the deck's claim that the MAPE ordering follows
    communication volume. On the measured data it does not, so the figure is
    drawn to show that plainly rather than to suggest a trend.
    """
    palette.apply_style()
    means = mean_migration(load_migration(data_dir), node_counts, per_rank)

    xs, ys, colours, markers, labels = [], [], [], [], []
    for _, row in means.iterrows():
        key = (row["scaling"], row["style"])
        if key not in MAPE:
            continue
        xs.append(row["migrated"])
        ys.append(MAPE[key])
        colours.append(STYLE_COLOUR[row["style"]])
        markers.append("o" if row["scaling"] == "strong" else "s")
        labels.append(f"{STYLE_LABEL[row['style']]}, {row['scaling']}")
    xs, ys = np.asarray(xs), np.asarray(ys)

    fig, ax = plt.subplots(figsize=(width, height))

    # No fitted line: the correlation is too weak for one to mean anything, and
    # drawing it would imply a trend the points do not show.
    pearson = float(np.corrcoef(xs, ys)[0, 1])
    ranks_x = pd.Series(xs).rank()
    ranks_y = pd.Series(ys).rank()
    spearman = float(np.corrcoef(ranks_x, ranks_y)[0, 1])

    # Join each style's strong and weak point. If communication volume set the
    # gap, these connectors would be short; that they are near-vertical is the
    # result.
    for style in STYLES:
        pair = means[means["style"] == style]
        if len(pair) != 2:
            continue
        px = [row["migrated"] for _, row in pair.iterrows()]
        py = [MAPE[(row["scaling"], row["style"])] for _, row in pair.iterrows()]
        ax.plot(px, py, color=STYLE_COLOUR[style], lw=0.8, alpha=0.35, zorder=1)

    for x, y, colour, marker, label in zip(xs, ys, colours, markers, labels, strict=True):
        ax.scatter(x, y, s=44, color=colour, marker=marker, zorder=3, linewidths=0)
        ax.annotate(
            label,
            xy=(x, y),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=7,
            color=palette.INK,
        )

    ax.set_xlabel(
        "mean particles migrated per step"
        + (" per rank" if per_rank else "")
    )
    ax.set_ylabel("MAPE against C [%]")
    # Headroom for the point labels, which sit up and to the right of each marker.
    ax.set_xlim(-0.03 * xs.max(), 1.42 * xs.max())
    ax.set_ylim(0, 1.14 * ys.max())
    ax.spines[["top", "right"]].set_visible(False)
    ax.text(
        0.98,
        0.04,
        f"Pearson $r = {pearson:+.2f}$\nSpearman $\\rho = {spearman:+.2f}$",
        transform=ax.transAxes,
        ha="right",
        fontsize=8,
        color="#6a6a6a",
    )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def summary(data_dir: Path, node_counts: list[int] | None = None) -> pd.DataFrame:
    """Table behind the two figures, for checking the numbers by eye."""
    frame = load_migration(data_dir)
    total = mean_migration(frame, node_counts).rename(
        columns={"migrated": "migrated_per_step"}
    )
    per_rank = mean_migration(frame, node_counts, per_rank=True).rename(
        columns={"migrated": "migrated_per_step_per_rank"}
    )
    merged = total.merge(per_rank, on=["scaling", "style"])
    merged["mape"] = [
        MAPE[(row["scaling"], row["style"])] for _, row in merged.iterrows()
    ]
    return merged.sort_values(["scaling", "migrated_per_step"])
