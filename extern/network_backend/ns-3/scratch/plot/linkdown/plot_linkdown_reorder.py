#!/usr/bin/env python3

from vtopo_packet_common import run_reorder_plot


if __name__ == "__main__":
    run_reorder_plot(
        x_values = [0, 1, 2, 4],
        series = {"path-pinning": [0, 0, 0, 0], 
            "random": [1.130125, 0.714250, 0.625219, 1.720687], 
            "DLB": [0.008000, 0.006406, 2.146531, 6.623437],
            "SGLB": [0.008000, 0.006406, 2.747862, 7.215462],},
        output_name="vtopo_packet_linkdown_reorder",
        x_label="Number of Failed Links",
    )
