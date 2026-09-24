"""Colours taken from the deck's cenatcolor.sty, so figures sit next to the
existing ones without a palette clash."""

NAVY = "#003366"
BLUE = "#0B75BD"
INK = "#262626"
GREY = "#E0E0E0"
RED = "#BE3C37"
GREEN = "#148C5F"
YELLOW = "#C89B14"

RUST = RED
C_LANG = BLUE

# Sequential ramp for anything ordered by minor radius: axis (navy) outwards to
# the last confined surface (yellow). Reads as one family in both light and dark
# projection, and stays distinguishable in greyscale.
RADIUS_RAMP = [NAVY, BLUE, GREEN, YELLOW]

# Eight distinguishable hues for colouring by MPI rank. Ranks are categorical,
# so this is a qualitative set rather than a ramp; it is desaturated to sit
# alongside the deck's navy and red without competing with them.
RANK_COLOURS = [
    "#1F4E79",
    "#2E86AB",
    "#3FA796",
    "#6BA644",
    "#C8992A",
    "#D4703A",
    "#B5495B",
    "#7B4B94",
]

MPL_RC = {
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "axes.linewidth": 0.7,
    "xtick.color": INK,
    "ytick.color": INK,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "legend.frameon": False,
    "text.color": INK,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
}


def radius_colormap():
    from matplotlib.colors import LinearSegmentedColormap

    return LinearSegmentedColormap.from_list("cenat_radius", RADIUS_RAMP)


def apply_style():
    import matplotlib.pyplot as plt

    plt.rcParams.update(MPL_RC)
