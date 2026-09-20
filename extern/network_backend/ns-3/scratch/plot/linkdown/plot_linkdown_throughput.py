#!/usr/bin/env python3

from vtopo_packet_common import run_throughput_plot


if __name__ == "__main__":
    run_throughput_plot(
        x_values = [0, 1, 2, 4],
        series = {"path-pinning": [190.691648, 176.841256, 162.990871, 135.290073], 
            "random": [190.132393, 178.945795, 167.419865, 105.287147], 
            "DLB": [190.690127, 179.252499, 165.348980, 99.655247],
            "SGLB": [190.695719, 179.252750, 164.438640, 95.432287],},
        ideal = [200.0, 187.5, 175.0, 150.0],
        output_name="vtopo_packet_linkdown_throughput",
        x_label="Number of Failed Links",
    )
