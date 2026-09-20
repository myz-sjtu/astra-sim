#!/usr/bin/env python3

from vtopo_packet_common import run_throughput_plot


if __name__ == "__main__":
    run_throughput_plot(
        experiment="linkdown",
        output_name="vtopo_packet_linkdown_throughput",
        x_label="Failed Links",
    )
