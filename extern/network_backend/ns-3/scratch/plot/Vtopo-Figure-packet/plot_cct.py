#!/usr/bin/env python3

from __future__ import annotations

import os
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")

from matplotlib import pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import FuncFormatter, MaxNLocator

from vtopo_packet_common import (
    AXIS_LABEL_FONT,
    ASYM_DELAY_DIRS,
    ASYM_DELAY_IDEAL_CONFIGS,
    ASYM_DELAY_X,
    FIGSIZE,
    LEGEND_FONT,
    LINKDOWN_DIRS,
    LINKDOWN_IDEAL_CONFIGS,
    LINKDOWN_X,
    STRATEGY_COLOR,
    STRATEGY_LABEL,
    STRATEGY_MARKER,
    STRATEGY_ORDER,
    Y_AXIS_LABEL_FONT,
    active_leaf_spine_capacity_gbps,
    apply_even_x_axis,
    build_parser,
    compact_float,
    data_rows,
    even_x_positions,
    parse_float,
    parse_int,
    read_flows,
    read_network_config,
    read_topology,
    style_axes,
)


Y_LABEL = "CCT (ms)"
IDEAL_LABEL = "Ideal CCT"
ANNOTATION_FONT = FontProperties(weight="bold", size=13)
MIN_SMALL_SPAN_CCT_WINDOW_MS = 2.0


@dataclass(frozen=True)
class FctRecord:
    src: int
    dst: int
    payload_bytes: int
    start_time_ns: int
    fct_ns: int
    standalone_fct_ns: int | None
    throughput_gbps: float | None


def read_fct_records(path: Path) -> list[FctRecord]:
    records: list[FctRecord] = []
    for line_number, parts in data_rows(path):
        if not parts[0][0].isdigit():
            continue
        if len(parts) >= 11:
            src_idx = 2
            dst_idx = 3
            payload_idx = 6
            start_idx = 7
            fct_idx = 8
            standalone_idx = 9
            throughput_idx = 10
        elif len(parts) >= 8:
            src_idx = 0
            dst_idx = 1
            payload_idx = 4
            start_idx = 5
            fct_idx = 6
            standalone_idx = 7
            throughput_idx = 8 if len(parts) > 8 else None
        else:
            raise ValueError(f"{path}:{line_number}: expected at least 8 FCT columns")

        records.append(
            FctRecord(
                src=parse_int(parts[src_idx], path, line_number, "src_id"),
                dst=parse_int(parts[dst_idx], path, line_number, "dst_id"),
                payload_bytes=parse_int(parts[payload_idx], path, line_number, "payload_bytes"),
                start_time_ns=parse_int(parts[start_idx], path, line_number, "start_time_ns"),
                fct_ns=parse_int(parts[fct_idx], path, line_number, "fct_ns"),
                standalone_fct_ns=parse_int(parts[standalone_idx], path, line_number, "standalone_fct_ns"),
                throughput_gbps=(
                    parse_float(parts[throughput_idx], path, line_number, "throughput_gbps")
                    if throughput_idx is not None
                    else None
                ),
            )
        )
    if not records:
        raise ValueError(f"{path}: no FCT records found")
    return records


def collection_completion_time_ms(result_dir: Path) -> float:
    records = read_fct_records(result_dir / "fct.txt")
    start_ns = min(record.start_time_ns for record in records)
    finish_ns = max(record.start_time_ns + record.fct_ns for record in records)
    return (finish_ns - start_ns) / 1e6


def effective_wire_bits(record: FctRecord) -> float:
    if record.throughput_gbps is not None and record.fct_ns > 0:
        return record.throughput_gbps * record.fct_ns
    return float(record.payload_bytes * 8)


def ideal_flow_rate_gbps(config_path: Path) -> dict[tuple[int, int], float]:
    config = read_network_config(config_path)
    topology = read_topology(config.topology_file)
    flows = read_flows(config.flow_file)

    flows_by_dst_leaf: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for flow in flows:
        if flow.dst not in topology.host_leaf:
            raise ValueError(f"{config.flow_file}: destination host {flow.dst} is not attached to a leaf")
        flows_by_dst_leaf[topology.host_leaf[flow.dst]].append((flow.src, flow.dst))

    rates: dict[tuple[int, int], float] = {}
    for dst_leaf, leaf_flows in flows_by_dst_leaf.items():
        active_capacity = active_leaf_spine_capacity_gbps(topology, config.link_down, dst_leaf)
        fair_share = active_capacity / len(leaf_flows) if leaf_flows else 0.0
        for src, dst in leaf_flows:
            rates[(src, dst)] = min(topology.host_rate_gbps[src], topology.host_rate_gbps[dst], fair_share)
    return rates


def ideal_collection_completion_time_ms(
    config_path: Path,
    reference_result_dir: Path,
    overhead_result_dir: Path | None = None,
) -> float:
    records = read_fct_records(reference_result_dir / "fct.txt")
    overhead_records = read_fct_records((overhead_result_dir or reference_result_dir) / "fct.txt")
    overhead_by_flow = {(record.src, record.dst): record for record in overhead_records}
    rates = ideal_flow_rate_gbps(config_path)
    start_ns = min(record.start_time_ns for record in records)
    finish_ns = start_ns

    for record in records:
        key = (record.src, record.dst)
        if key not in rates:
            raise ValueError(f"{config_path}: no ideal rate for flow {record.src}->{record.dst}")
        ideal_rate = rates[key]
        if ideal_rate <= 0:
            raise ValueError(f"{config_path}: non-positive ideal rate for flow {record.src}->{record.dst}")

        wire_bits = effective_wire_bits(record)
        pair_overhead_ns = 0.0
        overhead_record = overhead_by_flow.get(key)
        if overhead_record is not None and overhead_record.standalone_fct_ns is not None:
            base_rate = max(rates.values())
            overhead_wire_bits = effective_wire_bits(overhead_record)
            pair_overhead_ns = max(0.0, overhead_record.standalone_fct_ns - overhead_wire_bits / base_rate)
        ideal_fct_ns = pair_overhead_ns + wire_bits / ideal_rate
        finish_ns = max(finish_ns, record.start_time_ns + ideal_fct_ns)

    return (finish_ns - start_ns) / 1e6


def collect_cct_series(output_root: Path, experiment: str):
    if experiment == "linkdown":
        x_values = list(LINKDOWN_X)
        group = output_root / "multi-linkdown"
        dir_map = LINKDOWN_DIRS
        ideal_configs = LINKDOWN_IDEAL_CONFIGS
    elif experiment == "asym-delay":
        x_values = list(ASYM_DELAY_X)
        group = output_root / "asym-delay"
        dir_map = ASYM_DELAY_DIRS
        ideal_configs = ASYM_DELAY_IDEAL_CONFIGS
    else:
        raise ValueError(f"unknown experiment: {experiment}")

    series: dict[str, list[float]] = {strategy: [] for strategy in STRATEGY_ORDER}
    ideal: list[float] = []
    overhead_reference_dir = None
    if experiment == "asym-delay":
        overhead_reference_dir = group / dir_map[0]["path-pinning"]
    for x_value in x_values:
        for strategy in STRATEGY_ORDER:
            result_dir = group / dir_map[x_value][strategy]
            series[strategy].append(collection_completion_time_ms(result_dir))
        reference_dir = group / dir_map[x_value]["path-pinning"]
        ideal.append(
            ideal_collection_completion_time_ms(
                ideal_configs[x_value],
                reference_dir,
                overhead_reference_dir,
            )
        )
    return x_values, series, ideal


def print_summary(title: str, x_label: str, x_values, series, ideal) -> None:
    print(title)
    print(f"{x_label},strategy,{Y_LABEL}")
    for index, x_value in enumerate(x_values):
        for strategy in STRATEGY_ORDER:
            print(f"{x_value},{strategy},{series[strategy][index]:.6f}")
        print(f"{x_value},{IDEAL_LABEL},{ideal[index]:.6f}")


def cct_axis_limits(values: list[float]) -> tuple[float, float]:
    min_value = min(values)
    max_value = max(values)
    span = max_value - min_value
    if span < 1.0:
        step = 0.5
        target_span = max(MIN_SMALL_SPAN_CCT_WINDOW_MS, span * 1.35)
        midpoint = (min_value + max_value) / 2.0
        bottom = max(0.0, math.floor((midpoint - target_span / 2.0) / step) * step)
        top = math.ceil((midpoint + target_span / 2.0) / step) * step
        if top <= bottom:
            top = bottom + step
        return bottom, top
    elif span < 5.0:
        step = 0.5
        padding = max(span * 0.12, 0.25)
    elif span < 15.0:
        step = 1.0
        padding = max(span * 0.10, 0.75)
    else:
        step = 5.0
        padding = max(span * 0.05, 1.5)

    bottom = max(0.0, math.floor((min_value - padding) / step) * step)
    top = math.ceil((max_value + padding) / step) * step
    if top <= bottom:
        top = bottom + step
    return bottom, top


def apply_cct_scale(ax, values: list[float]) -> None:
    bottom, top = cct_axis_limits(values)
    ax.set_ylim(bottom=bottom, top=top)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: compact_float(value)))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6, steps=[1, 2, 2.5, 5, 10]))


def draw_panel(ax, x_values, series, ideal, x_label: str) -> None:
    x_positions = even_x_positions(x_values)
    all_values: list[float] = []
    for strategy in STRATEGY_ORDER:
        values = series[strategy]
        all_values.extend(values)
        ax.plot(
            x_positions,
            values,
            label=STRATEGY_LABEL[strategy],
            color=STRATEGY_COLOR[strategy],
            marker=STRATEGY_MARKER[strategy],
            markersize=7,
            linewidth=2.2,
        )

    all_values.extend(ideal)
    ax.plot(
        x_positions,
        ideal,
        label=IDEAL_LABEL,
        color="black",
        linestyle="--",
        marker="x",
        markersize=7,
        linewidth=2.0,
    )
    ax.annotate(
        IDEAL_LABEL,
        xy=(x_positions[-1], ideal[-1]),
        xytext=(-8, -8),
        textcoords="offset points",
        ha="right",
        va="top",
        fontproperties=ANNOTATION_FONT,
        color="black",
        clip_on=True,
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=0.2),
    )

    ax.set_xlabel(x_label, fontproperties=AXIS_LABEL_FONT)
    ax.set_ylabel(Y_LABEL, fontproperties=Y_AXIS_LABEL_FONT)
    apply_even_x_axis(ax, x_values)
    ax.margins(x=0.08)
    apply_cct_scale(ax, all_values)
    style_axes(ax)


def save_cct_figure(output_path: Path, x_values, series, ideal, x_label: str) -> None:
    fig, ax = plt.subplots(figsize=FIGSIZE)
    draw_panel(ax, x_values, series, ideal, x_label)

    ax.legend(
        prop=LEGEND_FONT,
        ncol=5,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.01),
        borderaxespad=0.0,
        framealpha=0.65,
        borderpad=0.3,
        columnspacing=1.4,
        handlelength=1.4,
        handletextpad=0.4,
        labelspacing=0.3,
    )
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)


def main() -> None:
    parser = build_parser("Plot collection completion time for Vtopo packet results.")
    args = parser.parse_args()

    link_x, link_series, link_ideal = collect_cct_series(args.output_root, "linkdown")
    asym_x, asym_series, asym_ideal = collect_cct_series(args.output_root, "asym-delay")

    link_output_path = args.out_dir / "vtopo_packet_cct_linkdown.pdf"
    asym_output_path = args.out_dir / "vtopo_packet_cct_asym_delay.pdf"
    save_cct_figure(link_output_path, link_x, link_series, link_ideal, "Failed Links")
    save_cct_figure(asym_output_path, asym_x, asym_series, asym_ideal, "Delay Imbalance (%)")

    if not args.no_summary:
        print_summary("vtopo_packet_cct_linkdown", "Failed Links", link_x, link_series, link_ideal)
        print_summary("vtopo_packet_cct_asym_delay", "Delay Imbalance (%)", asym_x, asym_series, asym_ideal)
    print(f"Saved {link_output_path}")
    print(f"Saved {asym_output_path}")


if __name__ == "__main__":
    main()
