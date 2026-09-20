#!/usr/bin/env python3

from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter

from plot_style import (
    AXIS_LABEL_FONT,
    FIGSIZE,
    add_legend,
    draw_grouped_bars,
    save_figure,
    style_category_axis,
)

filename = "large_pfc_duration"

# Values are in milliseconds. Order: PFC only, PFC+DCQCN, PFC+HPCC, PFC+Timely.
source_values = [85.606638, 5.360400, 24.973914, 14.080690]
remote_values = [176.504143, 3.134472, 27.294390, 12.013939]


def main():
    fig, ax = plt.subplots(figsize=FIGSIZE)
    handles = draw_grouped_bars(ax, source_values, remote_values)

    ax.set_ylabel("PFC Pause Duration (ms)", fontproperties=AXIS_LABEL_FONT)
    ax.set_yscale("log")
    positive_values = [value for group in [source_values, remote_values] for value in group if value > 0]
    if positive_values:
        ax.set_ylim(max(min(positive_values) * 0.5, 0.001), max(positive_values) * 2)
        ymin, ymax = ax.get_ylim()
        yticks = [1, 3, 10, 30, 100, 150, 300]
        ax.set_yticks([tick for tick in yticks if ymin <= tick <= ymax])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:g}"))

    style_category_axis(ax)
    add_legend(ax, handles)
    save_figure(fig, filename)


if __name__ == "__main__":
    main()
