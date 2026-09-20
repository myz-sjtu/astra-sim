#!/usr/bin/env python3

from vtopo_packet_common import run_reorder_plot


if __name__ == "__main__":
    run_reorder_plot(
        experiment="linkdown",
        output_name="vtopo_packet_linkdown_reorder",
        x_label="Number of Failed Links",
    )
