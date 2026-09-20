from matplotlib import pyplot as plt
import matplotlib as mpl
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Patch

mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42
mpl.rcParams["font.family"] = "serif"
mpl.rcParams["font.serif"] = ["Times New Roman", "DejaVu Serif"]
mpl.rcParams["mathtext.fontset"] = "stix"

FIGSIZE = (9, 5.5)
X_LABELS = ["PFC only", "PFC+DCQCN", "PFC+HPCC", "PFC+Timely"]
LEGENDS = ["Local Congestion", "Remote Congestion"]
X_POS = np.linspace(100, 200, len(X_LABELS))
BAR_WIDTH = 10

tab20_colors = plt.get_cmap("tab20").colors
COLORS = [tab20_colors[1], tab20_colors[7]]

AXIS_LABEL_FONT = FontProperties(weight="bold", size=22)
X_TICK_FONT = FontProperties(weight="bold", size=16)
Y_TICK_FONT = FontProperties(weight="bold", size=18)
LEGEND_FONT = FontProperties(weight="bold", size=16)
ANNOTATION_FONT = FontProperties(weight="bold", size=13)
NOTE_FONT = FontProperties(weight="bold", size=16)


def validate_series(source_values, remote_values):
    if len(source_values) != len(X_LABELS) or len(remote_values) != len(X_LABELS):
        raise ValueError("source_values and remote_values must each contain four values")


def draw_grouped_bars(ax, source_values, remote_values):
    validate_series(source_values, remote_values)
    handles = []
    for index, series in enumerate([source_values, remote_values]):
        ax.bar(
            X_POS + index * BAR_WIDTH,
            series,
            label="",
            color=COLORS[index],
            width=BAR_WIDTH,
            edgecolor="black",
            lw=1,
        )
        handles.append(Patch(facecolor=COLORS[index], edgecolor="black", label=LEGENDS[index]))
    return handles


def style_category_axis(ax, right_padding=BAR_WIDTH * 2):
    ax.set_xlim(X_POS[0] - BAR_WIDTH, X_POS[-1] + right_padding)
    ax.set_xticks(X_POS + BAR_WIDTH / 2)
    ax.set_xticklabels(X_LABELS, fontproperties=X_TICK_FONT)
    ax.tick_params(axis="y", labelsize=18)
    for label in ax.get_yticklabels():
        label.set_fontproperties(Y_TICK_FONT)
    ax.grid(True, linestyle="--", alpha=0.7)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("black")
        spine.set_linewidth(1.0)


def add_legend(ax, handles):
    ax.legend(
        handles=handles,
        prop=LEGEND_FONT,
        ncol=2,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.01),
        borderaxespad=0.0,
        framealpha=0.65,
        columnspacing=1.4,
        handlelength=1.4,
    )


def annotate_remote_gap(ax, remote_values, upper_bound=100, min_arrow_gap=6):
    remote_x = X_POS + BAR_WIDTH
    ax.axhline(y=upper_bound, color="gray", linestyle="--", linewidth=1.5, alpha=0.9)
    for x, value in zip(remote_x, remote_values):
        gap = upper_bound - value
        drop_ratio = gap / upper_bound * 100
        if gap < min_arrow_gap:
            bracket_x = x
            cap_half_width = BAR_WIDTH * 0.16
            ax.vlines(bracket_x, value, upper_bound, color="dimgray", linewidth=1.2)
            ax.hlines(
                [value, upper_bound],
                bracket_x - cap_half_width,
                bracket_x + cap_half_width,
                color="dimgray",
                linewidth=1.2,
            )
            label_x = bracket_x + cap_half_width
            text_offset = (4, 0)
        else:
            ax.annotate(
                "",
                xy=(x, upper_bound),
                xytext=(x, value),
                arrowprops=dict(arrowstyle="<->", color="dimgray", lw=1.2),
            )
            label_x = x
            text_offset = (6, 0)
        ax.annotate(
            f"{drop_ratio:.2f}%",
            xy=(label_x, value + gap / 2),
            xytext=text_offset,
            textcoords="offset points",
            ha="left",
            va="center",
            fontproperties=ANNOTATION_FONT,
            color="dimgray",
            clip_on=True,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=0.2),
        )


def save_figure(fig, filename):
    fig.tight_layout()
    fig.savefig(f"{filename}.pdf", bbox_inches="tight")
    plt.show()
