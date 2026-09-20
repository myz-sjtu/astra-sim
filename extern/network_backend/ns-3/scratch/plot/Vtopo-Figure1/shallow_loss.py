#!/usr/bin/env python3

from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter

from plot_style import (
    AXIS_LABEL_FONT,
    FIGSIZE,
    NOTE_FONT,
    add_legend,
    draw_grouped_bars,
    save_figure,
    style_category_axis,
)

filename = "shallow_loss"

# Values are packet loss rates in percent. Order: PFC only, PFC+DCQCN, PFC+HPCC, PFC+Timely.
source_values = [0.00035 * 100, 0.00035 * 100, 0.00035 * 100, 0.00035 * 100]
remote_values = [23.094730, 0.905427, 11.387189, 1.828060]


def main():
    fig, ax = plt.subplots(figsize=FIGSIZE)
    handles = draw_grouped_bars(ax, source_values, remote_values)

    ax.set_ylabel("Packet Loss Rate (%)", fontproperties=AXIS_LABEL_FONT)
    ax.set_yscale("log")
    ax.set_ylim(0.03, 25)
    ax.set_yticks([0.1, 1, 10, 25])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:g}%"))
    ax.axhline(y=0.035, color="gray", linestyle="--", linewidth=1.5, alpha=0.9)
    ax.text(
        0.02,
        0.035,
        "No Loss",
        transform=ax.get_yaxis_transform(),
        ha="left",
        va="bottom",
        fontproperties=NOTE_FONT,
        color="gray",
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=1.5),
    )

    style_category_axis(ax)
    add_legend(ax, handles)
    save_figure(fig, filename)


if __name__ == "__main__":
    main()
