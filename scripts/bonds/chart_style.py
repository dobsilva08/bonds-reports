"""Shared premium dark chart styling for Bonds Reports."""
import matplotlib.pyplot as plt

NAVY = "#101827"
PANEL = "#162235"
GRID = "#334155"
TEXT = "#E5E7EB"
MUTED = "#94A3B8"
BLUE = "#60A5FA"
GOLD = "#FBBF24"
GREEN = "#34D399"
RED = "#F87171"
PURPLE = "#A78BFA"

def apply_style():
    plt.rcParams.update({
        "figure.facecolor": NAVY, "axes.facecolor": PANEL,
        "axes.edgecolor": GRID, "axes.labelcolor": TEXT,
        "text.color": TEXT, "xtick.color": MUTED, "ytick.color": MUTED,
        "grid.color": GRID, "grid.alpha": .45,
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.titleweight": "bold", "axes.titlesize": 13,
        "legend.facecolor": PANEL, "legend.edgecolor": GRID,
        "savefig.facecolor": NAVY, "axes.grid": True,
        "axes.prop_cycle": plt.cycler(color=[BLUE, GOLD, GREEN, PURPLE, RED]),
    })

def finish(ax):
    ax.grid(True, alpha=.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
