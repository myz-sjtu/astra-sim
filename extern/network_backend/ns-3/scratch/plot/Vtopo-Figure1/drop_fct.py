#!/usr/bin/env python3

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path


DEFAULT_PACKET_PAYLOAD_SIZE = 1000


@dataclass(frozen=True)
class FlowRecord:
    payload_bytes: int
    start_time_ns: int
    fct_ns: int
    standalone_fct_ns: int | None
    throughput_gbps: float | None


@dataclass(frozen=True)
class DropRecord:
    switch_id: int
    drop_count: int


def parse_int(value: str, path: Path, line_number: int, field_name: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise ValueError(
            f"{path}:{line_number}: invalid {field_name}: {value!r}"
        ) from exc


def parse_float(value: str, path: Path, line_number: int, field_name: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(
            f"{path}:{line_number}: invalid {field_name}: {value!r}"
        ) from exc


def data_lines(path: Path):
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            yield line_number, stripped.split()


def read_fct(path: Path) -> list[FlowRecord]:
    """Read ASTRA-sim or HPCC-Dev fct.txt rows.

    Supported formats:
    - ASTRA-sim: sip_hex dip_hex src_id dst_id sport dport payload_bytes
      start_time_ns fct_ns standalone_fct_ns throughput_gbps
    - HPCC-Dev legacy: src_id dst_id sport dport payload_bytes start_time_ns
      fct_ns standalone_fct_ns [throughput_gbps]
    """
    flows: list[FlowRecord] = []
    for line_number, parts in data_lines(path):
        if not parts[0][0].isdigit():
            continue
        if len(parts) >= 11:
            payload_idx = 6
            start_idx = 7
            fct_idx = 8
            standalone_idx = 9
            throughput_idx = 10
        elif len(parts) >= 8:
            payload_idx = 4
            start_idx = 5
            fct_idx = 6
            standalone_idx = 7
            throughput_idx = 8 if len(parts) > 8 else None
        else:
            raise ValueError(
                f"{path}:{line_number}: expected at least 8 FCT columns, got {len(parts)}"
            )

        payload_bytes = parse_int(parts[payload_idx], path, line_number, "payload_bytes")
        start_time_ns = parse_int(parts[start_idx], path, line_number, "start_time_ns")
        fct_ns = parse_int(parts[fct_idx], path, line_number, "fct_ns")
        standalone_fct_ns = parse_int(
            parts[standalone_idx], path, line_number, "standalone_fct_ns"
        )
        throughput_gbps = (
            parse_float(parts[throughput_idx], path, line_number, "throughput_gbps")
            if throughput_idx is not None
            else None
        )
        if payload_bytes < 0:
            raise ValueError(f"{path}:{line_number}: payload_bytes must be non-negative")
        if fct_ns < 0:
            raise ValueError(f"{path}:{line_number}: fct_ns must be non-negative")
        flows.append(
            FlowRecord(
                payload_bytes=payload_bytes,
                start_time_ns=start_time_ns,
                fct_ns=fct_ns,
                standalone_fct_ns=standalone_fct_ns,
                throughput_gbps=throughput_gbps,
            )
        )
    if not flows:
        raise ValueError(f"{path}: no FCT records found")
    return flows


def read_drop(path: Path) -> list[DropRecord]:
    drops: list[DropRecord] = []
    for line_number, parts in data_lines(path):
        if len(parts) < 2:
            raise ValueError(
                f"{path}:{line_number}: expected at least 2 drop columns, got {len(parts)}"
            )
        if not parts[0][0].isdigit():
            continue
        switch_id = parse_int(parts[0], path, line_number, "switch_id")
        drop_count = parse_int(parts[1], path, line_number, "drop_count")
        if drop_count < 0:
            raise ValueError(f"{path}:{line_number}: drop_count must be non-negative")
        drops.append(DropRecord(switch_id=switch_id, drop_count=drop_count))
    if not drops:
        raise ValueError(f"{path}: no drop records found")
    return drops


def infer_drop_path(fct_path: Path) -> Path:
    name = fct_path.name
    if name.startswith("fct"):
        return fct_path.with_name("drop" + name[3:])
    return fct_path.with_name("drop.txt")


def parse_packet_payload_size(path: Path) -> int:
    for line_number, parts in data_lines(path):
        if parts[0] != "PACKET_PAYLOAD_SIZE":
            continue
        if len(parts) < 2:
            raise ValueError(f"{path}:{line_number}: PACKET_PAYLOAD_SIZE needs a value")
        value = parse_int(parts[1], path, line_number, "PACKET_PAYLOAD_SIZE")
        if value <= 0:
            raise ValueError(f"{path}:{line_number}: PACKET_PAYLOAD_SIZE must be positive")
        return value
    raise ValueError(f"{path}: PACKET_PAYLOAD_SIZE not found")


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentile(values: list[int], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * percentile_value / 100.0
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return float(ordered[lower])
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compute switch packet drop rate and average FCT from fct.txt/drop.txt."
    )
    parser.add_argument(
        "--fct",
        type=Path,
        help="Path to fct.txt or fctN.txt. Matching drop.txt/dropN.txt is inferred by default.",
    )
    parser.add_argument(
        "--drop",
        type=Path,
        help="Path to drop.txt. Defaults to the matching file next to fct.txt.",
    )
    parser.add_argument(
        "--packet-payload-size",
        type=int,
        default=DEFAULT_PACKET_PAYLOAD_SIZE,
        help=f"RDMA data payload bytes per packet. Default: {DEFAULT_PACKET_PAYLOAD_SIZE}.",
    )
    parser.add_argument(
        "--network-config",
        type=Path,
        help="Optional network_config.txt; PACKET_PAYLOAD_SIZE overrides --packet-payload-size.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    fct_path = args.fct
    drop_path = args.drop or infer_drop_path(fct_path)
    if not fct_path.exists():
        parser.error(f"FCT file not found: {fct_path}")
    if not drop_path.exists():
        parser.error(f"Drop file not found: {drop_path}")
    if args.packet_payload_size <= 0:
        parser.error("--packet-payload-size must be positive")
    if args.network_config is not None and not args.network_config.exists():
        parser.error(f"Network config file not found: {args.network_config}")

    try:
        packet_payload_size = args.packet_payload_size
        if args.network_config is not None:
            packet_payload_size = parse_packet_payload_size(args.network_config)
        flows = read_fct(fct_path)
        drops = read_drop(drop_path)
    except ValueError as exc:
        parser.exit(2, f"error: {exc}\n")

    total_payload_bytes = sum(flow.payload_bytes for flow in flows)
    delivered_data_packets = sum(
        math.ceil(flow.payload_bytes / packet_payload_size) for flow in flows
    )
    total_drop_packets = sum(record.drop_count for record in drops)
    attempted_data_packets = delivered_data_packets + total_drop_packets
    drop_rate = (
        total_drop_packets / attempted_data_packets if attempted_data_packets > 0 else 0.0
    )

    fct_values = [flow.fct_ns for flow in flows]
    standalone_values = [
        flow.standalone_fct_ns for flow in flows if flow.standalone_fct_ns is not None
    ]
    throughput_values = [
        flow.throughput_gbps for flow in flows if flow.throughput_gbps is not None
    ]
    slowdown_values = [
        flow.fct_ns / flow.standalone_fct_ns
        for flow in flows
        if flow.standalone_fct_ns is not None and flow.standalone_fct_ns > 0
    ]
    window_start_ns = min(flow.start_time_ns for flow in flows)
    window_end_ns = max(flow.start_time_ns + flow.fct_ns for flow in flows)

    print(f"fct_file {fct_path}")
    print(f"drop_file {drop_path}")
    print(f"packet_payload_size {packet_payload_size}")
    print(f"flow_count {len(flows)}")
    print(f"total_payload_bytes {total_payload_bytes}")
    print(f"delivered_data_packets_est {delivered_data_packets}")
    print(f"switch_drop_packets {total_drop_packets}")
    print(f"attempted_data_packets_est {attempted_data_packets}")
    print(f"drop_rate {drop_rate:.12g}")
    print(f"drop_percent {drop_rate * 100.0:.6f}%")
    print(f"avg_fct_ns {mean([float(value) for value in fct_values]):.6f}")
    print(f"avg_fct_ms {mean([value / 1e6 for value in fct_values]):.6f}")
    print(f"min_fct_ms {min(fct_values) / 1e6:.6f}")
    print(f"p50_fct_ms {percentile(fct_values, 50) / 1e6:.6f}")
    print(f"p95_fct_ms {percentile(fct_values, 95) / 1e6:.6f}")
    print(f"max_fct_ms {max(fct_values) / 1e6:.6f}")
    print(f"flow_window_ns {window_end_ns - window_start_ns}")
    print(f"flow_window_ms {(window_end_ns - window_start_ns) / 1e6:.6f}")
    if standalone_values:
        print(f"avg_standalone_fct_ms {mean([value / 1e6 for value in standalone_values]):.6f}")
    if slowdown_values:
        print(f"avg_fct_slowdown {mean(slowdown_values):.12g}")
    if throughput_values:
        print(f"avg_throughput_gbps {mean(throughput_values):.6f}")


if __name__ == "__main__":
    main()
