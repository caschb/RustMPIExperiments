"""Link-time optimisation on both sides of the Rust-versus-C comparison.

The deck's results have LTO off for both languages and blame the PIC gap on
un-inlined RSMPI wrappers. These figures answer the follow-up question: the
same PIC styles and BS-SOLCTRA strong scaling, each language built with and
without LTO by the same compilers, the four binaries run back to back inside
one allocation. Input is the results.csv that lto/parse-results.py writes.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import palette

STYLES = ["GEOMETRIC", "SINUSOIDAL", "LINEAR", "PATCH"]
STYLE_LABEL = {s: s.capitalize() for s in STYLES}
SCALINGS = ["strong", "weak"]
LANGS = ["c", "rust"]
LANG_LABEL = {"c": "C", "rust": "Rust"}
LANG_COLOUR = {"c": palette.C_LANG, "rust": palette.RUST}

# Identity is carried by hue (language) and by line/marker style (LTO), so the
# two states of one language never rely on a shade difference.
LTO_STYLE = {
    0: dict(linestyle=(0, (3, 2)), markerfacecolor="white", label="no LTO"),
    1: dict(linestyle="-", label="LTO"),
}
GRID = dict(color=palette.GREY, linewidth=0.6)
ERR = dict(elinewidth=0.7, capsize=2, capthick=0.7)


def load(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, keep_default_na=False)
    frame["lto"] = frame["lto"].astype(int)
    return frame


def summarise(frame: pd.DataFrame) -> pd.DataFrame:
    keys = ["code", "lang", "lto", "nodes", "ranks", "scaling", "style"]
    out = frame.groupby(keys, as_index=False)["metric"].agg(
        mean="mean", sd="std", n="count"
    )
    out["sd"] = out["sd"].fillna(0.0)
    return out


def paired_lto_ratio(frame: pd.DataFrame) -> pd.DataFrame:
    """LTO gain per repetition, LTO over no-LTO for rates and the inverse for
    times, so that >1 always means LTO helped. Repetitions are paired because
    the two binaries ran back to back, which removes the slow drift between
    repetitions that a ratio of means would fold into the spread."""
    keys = ["code", "lang", "nodes", "ranks", "scaling", "style", "rep"]
    wide = frame.pivot_table(index=keys, columns="lto", values="metric").dropna()
    wide = wide.reset_index()
    higher_is_better = wide["code"] == "pic"
    wide["ratio"] = np.where(
        higher_is_better, wide[1] / wide[0], wide[0] / wide[1]
    )
    group = keys[:-1]
    return wide.groupby(group, as_index=False)["ratio"].agg(
        mean="mean", sd="std", n="count"
    ).fillna({"sd": 0.0})


def mape_over_nodes(summary: pd.DataFrame) -> pd.DataFrame:
    """The deck's similarity metric: mean over node counts of the absolute
    percentage difference of the Rust mean from the C mean."""
    keys = ["code", "lto", "scaling", "style", "nodes"]
    wide = summary.pivot_table(index=keys, columns="lang", values="mean").dropna()
    wide = wide.reset_index()
    wide["ape"] = 100.0 * (wide["rust"] - wide["c"]).abs() / wide["c"]
    return wide.groupby(["code", "lto", "scaling", "style"], as_index=False)[
        "ape"
    ].agg(mape="mean", n="count")


def _panel_grid(nrows: int, ncols: int, width: float, height: float, sharex: bool = True):
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(width, height), sharex=sharex, squeeze=False
    )
    for ax in axes.flat:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", **GRID)
        ax.set_axisbelow(True)
    return fig, axes


def _four_series_legend(fig, ncol: int = 4, y: float = -0.02):
    from matplotlib.lines import Line2D

    handles = []
    for lang in LANGS:
        for lto in (0, 1):
            style = LTO_STYLE[lto]
            handles.append(
                Line2D(
                    [], [], color=LANG_COLOUR[lang], marker="o", markersize=4,
                    linewidth=1.4, linestyle=style["linestyle"],
                    markerfacecolor=style.get("markerfacecolor", LANG_COLOUR[lang]),
                    label=f"{LANG_LABEL[lang]}, {style['label']}",
                )
            )
    fig.legend(handles=handles, loc="lower center", ncol=ncol, bbox_to_anchor=(0.5, y))


def plot_pic_rates(summary: pd.DataFrame, out: Path) -> Path:
    palette.apply_style()
    pic = summary[summary["code"] == "pic"]
    fig, axes = _panel_grid(2, 4, 7.2, 3.9)
    for r, scaling in enumerate(SCALINGS):
        for c, style in enumerate(STYLES):
            ax = axes[r, c]
            sub = pic[(pic["scaling"] == scaling) & (pic["style"] == style)]
            for lang in LANGS:
                for lto in (0, 1):
                    s = sub[(sub["lang"] == lang) & (sub["lto"] == lto)].sort_values("ranks")
                    if s.empty:
                        continue
                    ax.errorbar(
                        s["ranks"], s["mean"], yerr=s["sd"], color=LANG_COLOUR[lang],
                        marker="o", markersize=4, linewidth=1.4,
                        linestyle=LTO_STYLE[lto]["linestyle"],
                        markerfacecolor=LTO_STYLE[lto].get("markerfacecolor", LANG_COLOUR[lang]),
                        **ERR,
                    )
            ax.set_xticks([20, 40, 80])
            ax.set_ylim(bottom=0)
            if r == 0:
                ax.set_title(STYLE_LABEL[style])
            if c == 0:
                ax.set_ylabel(f"{scaling} scaling\nRate (Mparticles/s)")
            if r == 1:
                ax.set_xlabel("Ranks")
    _four_series_legend(fig)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(out)
    plt.close(fig)
    return out


def _ratio_bars(ax, ratios: pd.DataFrame, xcol: str, xvals: list, label_first: bool):
    """Gain bars grow from the 1.0 baseline, so a loss points down instead of
    being a slightly shorter bar on a truncated axis."""
    width = 0.32
    xs = np.arange(len(xvals))
    for i, lang in enumerate(LANGS):
        s = ratios[ratios["lang"] == lang].set_index(xcol).reindex(xvals)
        offset = (i - 0.5) * (width + 0.04)
        mean = s["mean"].to_numpy(dtype=float)
        ok = ~np.isnan(mean)
        ax.bar(
            xs[ok] + offset, mean[ok] - 1.0, width, bottom=1.0,
            color=LANG_COLOUR[lang], yerr=s["sd"].to_numpy(dtype=float)[ok],
            error_kw=dict(ecolor=palette.INK, **ERR),
            label=LANG_LABEL[lang] if label_first else None, linewidth=0,
        )
    ax.axhline(1.0, color=palette.INK, linewidth=0.7)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(v) for v in xvals])


def _ratio_limits(ratios: pd.DataFrame) -> tuple[float, float]:
    if ratios.empty:
        return 0.9, 1.1
    lo = float(np.floor((ratios["mean"] - ratios["sd"]).min() * 20) / 20)
    hi = float(np.ceil((ratios["mean"] + ratios["sd"]).max() * 20) / 20)
    return min(0.9, lo), max(1.1, hi)


def plot_pic_speedup(ratios: pd.DataFrame, out: Path) -> Path:
    palette.apply_style()
    pic = ratios[ratios["code"] == "pic"]
    fig, axes = _panel_grid(2, 4, 7.2, 3.7)
    nodes = sorted(pic["nodes"].unique()) or [1, 2, 4]
    lo, hi = _ratio_limits(pic)
    for r, scaling in enumerate(SCALINGS):
        for c, style in enumerate(STYLES):
            ax = axes[r, c]
            sub = pic[(pic["scaling"] == scaling) & (pic["style"] == style)]
            _ratio_bars(ax, sub, "nodes", nodes, label_first=(r == 0 and c == 0))
            ax.set_ylim(lo, hi)
            if r == 0:
                ax.set_title(STYLE_LABEL[style])
            if c == 0:
                ax.set_ylabel(f"{scaling} scaling\nLTO gain")
            if r == 1:
                ax.set_xlabel("Nodes")
    fig.supxlabel("Gain = rate with LTO / rate without, paired by repetition", fontsize=8, y=0.06)
    fig.legend(loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.03))
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    fig.savefig(out)
    plt.close(fig)
    return out


def plot_pic_mape(mape: pd.DataFrame, out: Path) -> Path:
    """Emphasis form: the LTO bar in the language-neutral blue, the no-LTO bar
    in grey, each bar direct-labelled so the grey never has to carry a value."""
    palette.apply_style()
    pic = mape[mape["code"] == "pic"]
    fig, axes = _panel_grid(1, 2, 7.2, 2.6)
    width = 0.34
    colours = {0: "#8C8C8C", 1: palette.BLUE}
    labels = {0: "no LTO", 1: "LTO"}
    xs = np.arange(len(STYLES))
    for c, scaling in enumerate(SCALINGS):
        ax = axes[0, c]
        sub = pic[pic["scaling"] == scaling]
        for lto in (0, 1):
            s = sub[sub["lto"] == lto].set_index("style").reindex(STYLES)
            offset = (lto - 0.5) * (width + 0.04)
            bars = ax.bar(
                xs + offset, s["mape"].fillna(0), width, color=colours[lto],
                label=labels[lto] if c == 0 else None, linewidth=0,
            )
            for bar, value in zip(bars, s["mape"]):
                if pd.notna(value):
                    ax.annotate(
                        f"{value:.1f}", (bar.get_x() + bar.get_width() / 2, value),
                        xytext=(0, 2), textcoords="offset points",
                        ha="center", va="bottom", fontsize=7, color=palette.INK,
                    )
        ax.set_xticks(xs)
        ax.set_xticklabels([STYLE_LABEL[s] for s in STYLES])
        ax.set_title(f"{scaling} scaling")
        if c == 0:
            ax.set_ylabel("MAPE, Rust vs C (%)")
    top = float(pic["mape"].max()) if len(pic) else 10.0
    for ax in axes.flat:
        ax.set_ylim(0, top * 1.18)
    fig.legend(loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(out)
    plt.close(fig)
    return out


def plot_solctra(summary: pd.DataFrame, ratios: pd.DataFrame, out: Path) -> Path:
    palette.apply_style()
    sol = summary[summary["code"] == "solctra"]
    rat = ratios[ratios["code"] == "solctra"]
    fig, axes = _panel_grid(1, 2, 6.0, 2.8, sharex=False)
    ax = axes[0, 0]
    for lang in LANGS:
        for lto in (0, 1):
            s = sol[(sol["lang"] == lang) & (sol["lto"] == lto)].sort_values("nodes")
            if s.empty:
                continue
            ax.errorbar(
                s["nodes"], s["mean"], yerr=s["sd"], color=LANG_COLOUR[lang],
                marker="o", markersize=4, linewidth=1.4,
                linestyle=LTO_STYLE[lto]["linestyle"],
                markerfacecolor=LTO_STYLE[lto].get("markerfacecolor", LANG_COLOUR[lang]),
                **ERR,
            )
    ax.set_xticks([1, 2, 4])
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Nodes")
    ax.set_ylabel("Time (s)")
    ax.set_title("Strong scaling")

    ax = axes[0, 1]
    nodes = sorted(rat["nodes"].unique()) or [1, 2, 4]
    _ratio_bars(ax, rat, "nodes", nodes, label_first=True)
    ax.set_ylim(*_ratio_limits(rat))
    # The gains sit within a few tenths of a percent of 1.0, so per-bar labels
    # collide and say the same thing; one line states the bound instead.
    if len(rat):
        bound = 100 * float((rat["mean"] - 1).abs().max())
        ax.text(
            0.5, 0.97, f"LTO changes the time by at most {bound:.1f}%",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.5,
            color=palette.INK,
        )
    ax.set_xlabel("Nodes")
    ax.set_ylabel("LTO gain")
    ax.set_title("Gain from LTO")
    ax.legend(loc="lower left")
    fig.supxlabel(
        "61440 particles, 1000 steps, 1 rank per node, 20 threads. "
        "Gain = time without LTO / time with, paired by repetition",
        fontsize=8, y=0.07,
    )
    _four_series_legend(fig, ncol=4, y=-0.03)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(out)
    plt.close(fig)
    return out


def render_all(results: Path, out_dir: Path) -> list[Path]:
    frame = load(results)
    summary = summarise(frame)
    ratios = paired_lto_ratio(frame)
    mape = mape_over_nodes(summary)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = [
        plot_pic_rates(summary, out_dir / "pic_lto_rates.pdf"),
        plot_pic_speedup(ratios, out_dir / "pic_lto_speedup.pdf"),
        plot_pic_mape(mape, out_dir / "pic_lto_mape.pdf"),
    ]
    if (frame["code"] == "solctra").any():
        written.append(plot_solctra(summary, ratios, out_dir / "solctra_lto.pdf"))
    return written


def print_summary(results: Path) -> None:
    frame = load(results)
    summary = summarise(frame)
    ratios = paired_lto_ratio(frame)
    mape = mape_over_nodes(summary)
    with pd.option_context("display.width", 200, "display.max_rows", 500):
        print("Per configuration, mean +/- sd (n):")
        print(summary.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
        print("\nPaired LTO gain (>1 means LTO helped):")
        print(ratios.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
        print("\nMAPE of Rust against C over node counts:")
        print(mape.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
