#!/usr/bin/env python3
"""Plot ARN switch egress-port queue and load monitor CSV output."""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
from collections import defaultdict
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "astra-sim-matplotlib")
)

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError as exc:
    raise SystemExit(
        "matplotlib is required for plotting. Rebuild the Docker image with "
        "matplotlib installed, or install it in the active Python environment."
    ) from exc


QUEUE_METRICS = ("port_queue_bytes", "max_queue_bytes")
LOAD_METRICS = ("load_Bps", "load_ratio")
ALL_METRICS = QUEUE_METRICS + LOAD_METRICS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot qlen/load time series from QLEN_MON_FILE CSV output."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to qlen/load monitor CSV, e.g. scratch/output/case/qlen.txt.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for PNG plots. Defaults to <input parent>/plots.",
    )
    parser.add_argument(
        "--switch-id",
        type=int,
        help="Only plot one switch ID.",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Only plot one egress port/interface index.",
    )
    parser.add_argument(
        "--metric",
        choices=("all", "queue", "load") + ALL_METRICS,
        default="all",
        help="Metric group or single metric to plot.",
    )
    return parser.parse_args()


def read_rows(path: Path, switch_id: int | None, port: int | None) -> list[dict]:
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {
            "time_ns",
            "switch_id",
            "switch_role",
            "out_dev",
            "neighbor_node_id",
            "port_queue_bytes",
            "max_queue_index",
            "max_queue_bytes",
            "load_Bps",
            "load_ratio",
            "link_rate_bps",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"missing required CSV columns: {sorted(missing)}")

        for row in reader:
            row_switch_id = int(row["switch_id"])
            row_port = int(row["out_dev"])
            if switch_id is not None and row_switch_id != switch_id:
                continue
            if port is not None and row_port != port:
                continue
            row["_time_s"] = int(row["time_ns"]) / 1_000_000_000.0
            row["_switch_id"] = row_switch_id
            row["_out_dev"] = row_port
            for metric in ALL_METRICS:
                row[metric] = float(row[metric])
            rows.append(row)
    if not rows:
        raise SystemExit("no rows matched the input filters")
    return rows


def group_rows(rows: list[dict]) -> dict[int, dict[int, list[dict]]]:
    grouped: dict[int, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row["_switch_id"]][row["_out_dev"]].append(row)
    for ports in grouped.values():
        for port_rows in ports.values():
            port_rows.sort(key=lambda item: item["_time_s"])
    return grouped


def plot_metric_group(
    output_dir: Path,
    switch_id: int,
    ports: dict[int, list[dict]],
    metrics: tuple[str, ...],
    name: str,
) -> None:
    fig, axes = plt.subplots(
        len(metrics),
        1,
        figsize=(12, 3.6 * len(metrics)),
        sharex=True,
        squeeze=False,
    )
    for axis, metric in zip(axes[:, 0], metrics):
        for port, port_rows in sorted(ports.items()):
            times = [row["_time_s"] for row in port_rows]
            values = [row[metric] for row in port_rows]
            axis.plot(times, values, label=f"port {port}", linewidth=1.2)
        axis.set_ylabel(metric)
        axis.grid(True, linewidth=0.3, alpha=0.5)
    axes[-1, 0].set_xlabel("time (s)")
    axes[0, 0].set_title(f"switch {switch_id} {name}")
    axes[0, 0].legend(loc="best", fontsize="small", ncol=2)
    fig.tight_layout()
    fig.savefig(output_dir / f"switch_{switch_id}_{name}.png", dpi=160)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir or args.input.parent / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = read_rows(args.input, args.switch_id, args.port)
    grouped = group_rows(rows)

    if args.metric == "all":
        metric_groups = (("queue", QUEUE_METRICS), ("load", LOAD_METRICS))
    elif args.metric == "queue":
        metric_groups = (("queue", QUEUE_METRICS),)
    elif args.metric == "load":
        metric_groups = (("load", LOAD_METRICS),)
    else:
        metric_groups = ((args.metric, (args.metric,)),)

    for switch_id, ports in sorted(grouped.items()):
        for name, metrics in metric_groups:
            plot_metric_group(output_dir, switch_id, ports, metrics, name)

    print(f"wrote plots to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
