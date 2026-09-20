#!/usr/bin/env python3

from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter

from plot_style import (
    AXIS_LABEL_FONT,
    BAR_WIDTH,
    FIGSIZE,
    add_legend,
    annotate_remote_gap,
    draw_grouped_bars,
    save_figure,
    style_category_axis,
)

filename = "large_bw"

# Order: PFC only, PFC+DCQCN, PFC+HPCC, PFC+Timely.
source_values = [97.573291, 59.065244, 91.307196, 97.591715]
remote_values = [82.431447, 59.060841, 94.890305, 96.314191]


def main():
    fig, ax = plt.subplots(figsize=FIGSIZE)
    handles = draw_grouped_bars(ax, source_values, remote_values)

    annotate_remote_gap(ax, remote_values)
    ax.set_ylabel("Throughput (Gbps)", fontproperties=AXIS_LABEL_FONT)
    ax.set_ylim(0, 120)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.0f}"))

    style_category_axis(ax, right_padding=BAR_WIDTH * 2.7)
    add_legend(ax, handles)
    save_figure(fig, filename)


if __name__ == "__main__":
    main()
