#!/usr/bin/env python3

from vtopo_packet_common import run_reorder_plot


if __name__ == "__main__":
    run_reorder_plot(
        experiment="asym-delay",
        output_name="vtopo_packet_asym_delay_reorder",
        x_label="Delay Imbalance (%)",
        default_yscale="linear",
    )
