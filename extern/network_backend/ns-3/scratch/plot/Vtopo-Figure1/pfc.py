#!/usr/bin/env python3

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FlowWindow:
    flow_count: int
    start_ns: int
    end_ns: int

    @property
    def duration_ns(self) -> int:
        return self.end_ns - self.start_ns


@dataclass(frozen=True)
class PfcSummary:
    pause_events: int
    resume_events: int
    duplicate_pause_events: int
    unmatched_resume_events: int
    open_intervals_closed: int
    observed_paused_ports: int
    peak_concurrent_paused_ports: int
    total_pause_port_ns: int


def parse_int(value: str, path: Path, line_number: int, field_name: str) -> int:
    try:
        return int(value, 0)
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


def parse_fct_window(path: Path) -> FlowWindow:
    """Return the active flow window from fct.txt.

    Supported fct.txt formats:
    - ASTRA-sim: sip_hex dip_hex src_id dst_id sport dport payload_bytes
      start_time_ns fct_ns standalone_fct_ns throughput_gbps
    - HPCC-Dev legacy: src_id dst_id sport dport payload_bytes start_time_ns
      fct_ns standalone_fct_ns
    """
    flow_count = 0
    min_start_ns: int | None = None
    max_finish_ns = 0
    max_fct_ns = 0

    for line_number, parts in data_lines(path):
        if not parts[0][0].isdigit():
            continue

        if len(parts) >= 11:
            start_idx = 7
            fct_idx = 8
        elif len(parts) >= 8:
            start_idx = 5
            fct_idx = 6
        else:
            raise ValueError(
                f"{path}:{line_number}: expected at least 8 FCT columns, got {len(parts)}"
            )

        start_ns = parse_int(parts[start_idx], path, line_number, "start_time_ns")
        fct_ns = parse_int(parts[fct_idx], path, line_number, "fct_ns")
        if fct_ns < 0:
            raise ValueError(f"{path}:{line_number}: fct_ns must be non-negative")

        flow_count += 1
        min_start_ns = start_ns if min_start_ns is None else min(min_start_ns, start_ns)
        max_finish_ns = max(max_finish_ns, start_ns + fct_ns)
        max_fct_ns = max(max_fct_ns, fct_ns)

    if flow_count == 0:
        raise ValueError(f"{path}: no FCT records found")

    assert min_start_ns is not None
    if max_finish_ns <= min_start_ns or max_fct_ns <= 0:
        raise ValueError(f"{path}: computed non-positive flow window")
    return FlowWindow(flow_count=flow_count, start_ns=min_start_ns, end_ns=max_finish_ns)


def clip_interval(
    start_ns: int,
    end_ns: int,
    window_start_ns: int,
    window_end_ns: int,
) -> tuple[int, int] | None:
    start = max(start_ns, window_start_ns)
    end = min(end_ns, window_end_ns)
    if end <= start:
        return None
    return start, end


def peak_concurrent_ports(intervals: list[tuple[int, int]]) -> int:
    points: list[tuple[int, int]] = []
    for start_ns, end_ns in intervals:
        points.append((start_ns, 1))
        points.append((end_ns, -1))
    active = 0
    peak = 0
    for _, delta in sorted(points, key=lambda item: (item[0], item[1])):
        active += delta
        peak = max(peak, active)
    return peak


def parse_pfc_duration(path: Path, window: FlowWindow) -> PfcSummary:
    """Pair pause/resume events and return port-time pause duration.

    PFC is a per-port signal, not a per-flow signal. The numerator is therefore
    paused port-time: sum(duration of each paused receiving port), clipped to the
    active flow window. Concurrent pauses on N ports contribute N ns per ns.
    """
    open_since: dict[tuple[str, str, str], int] = {}
    paused_ports: set[tuple[str, str, str]] = set()
    intervals: list[tuple[int, int]] = []
    pause_events = 0
    resume_events = 0
    duplicate_pause_events = 0
    unmatched_resume_events = 0
    open_intervals_closed = 0

    for line_number, parts in data_lines(path):
        if len(parts) < 5:
            raise ValueError(
                f"{path}:{line_number}: expected at least 5 PFC columns, got {len(parts)}"
            )
        time_ns = parse_int(parts[0], path, line_number, "time_ns")
        dst_node = parts[1]
        node_type = parts[2]
        if_index = parts[3]
        frame = parts[4]
        key = (dst_node, node_type, if_index)

        if frame == "1":
            pause_events += 1
            if key in open_since:
                duplicate_pause_events += 1
                continue
            open_since[key] = time_ns
        elif frame == "0":
            resume_events += 1
            start_ns = open_since.pop(key, None)
            if start_ns is None:
                unmatched_resume_events += 1
                continue
            clipped = clip_interval(start_ns, time_ns, window.start_ns, window.end_ns)
            if clipped is not None:
                intervals.append(clipped)
                paused_ports.add(key)
        else:
            raise ValueError(
                f"{path}:{line_number}: PFC frame must be 1=pause or 0=resume"
            )

    for key, start_ns in open_since.items():
        open_intervals_closed += 1
        clipped = clip_interval(start_ns, window.end_ns, window.start_ns, window.end_ns)
        if clipped is not None:
            intervals.append(clipped)
            paused_ports.add(key)

    total_pause_port_ns = sum(end_ns - start_ns for start_ns, end_ns in intervals)
    return PfcSummary(
        pause_events=pause_events,
        resume_events=resume_events,
        duplicate_pause_events=duplicate_pause_events,
        unmatched_resume_events=unmatched_resume_events,
        open_intervals_closed=open_intervals_closed,
        observed_paused_ports=len(paused_ports),
        peak_concurrent_paused_ports=peak_concurrent_ports(intervals),
        total_pause_port_ns=total_pause_port_ns,
    )


def parse_topology_port_count(path: Path) -> int:
    numeric_rows: list[list[str]] = []
    for _, parts in data_lines(path):
        if parts and parts[0].isdigit():
            numeric_rows.append(parts)
    if not numeric_rows:
        raise ValueError(f"{path}: topology file has no numeric header")
    header = numeric_rows[0]
    if len(header) >= 4:
        link_count = parse_int(header[3], path, 1, "link_count")
    elif len(header) >= 3:
        link_count = parse_int(header[2], path, 1, "link_count")
    else:
        raise ValueError(f"{path}: topology header is too short")
    if link_count <= 0:
        raise ValueError(f"{path}: topology link_count must be positive")
    return link_count * 2


def infer_pfc_path(fct_path: Path) -> Path:
    name = fct_path.name
    if name.startswith("fct"):
        return fct_path.with_name("pfc" + name[3:])
    return fct_path.with_name("pfc.txt")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compute PFC pause duration from fct.txt and pfc.txt."
    )
    parser.add_argument(
        "--fct",
        type=Path,
        help="Path to fct.txt or fctN.txt. The matching pfc.txt/pfcN.txt is inferred by default.",
    )
    parser.add_argument(
        "--pfc",
        type=Path,
        help="Path to pfc.txt. Defaults to the matching file next to fct.txt.",
    )
    parser.add_argument(
        "--port-count",
        type=int,
        help="Total directional QBB port count for network-wide normalization.",
    )
    parser.add_argument(
        "--topology",
        type=Path,
        help="Topology file used to infer directional port count as 2 * link_count.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    fct_path = args.fct
    pfc_path = args.pfc or infer_pfc_path(fct_path)
    if args.port_count is not None and args.topology is not None:
        parser.error("use only one of --port-count or --topology")
    if args.port_count is not None and args.port_count <= 0:
        parser.error("--port-count must be positive")
    if not fct_path.exists():
        parser.error(f"FCT file not found: {fct_path}")
    if not pfc_path.exists():
        parser.error(f"PFC file not found: {pfc_path}")
    if args.topology is not None and not args.topology.exists():
        parser.error(f"Topology file not found: {args.topology}")

    try:
        window = parse_fct_window(fct_path)
        summary = parse_pfc_duration(pfc_path, window)
        normalized_port_count = args.port_count
        if args.topology is not None:
            normalized_port_count = parse_topology_port_count(args.topology)
    except ValueError as exc:
        parser.exit(2, f"error: {exc}\n")

    pfc_duration_ratio = summary.total_pause_port_ns / window.duration_ns
    observed_port_pause_fraction = (
        summary.total_pause_port_ns / (summary.observed_paused_ports * window.duration_ns)
        if summary.observed_paused_ports > 0
        else None
    )
    network_port_pause_fraction = (
        summary.total_pause_port_ns / (normalized_port_count * window.duration_ns)
        if normalized_port_count is not None
        else None
    )

    print(f"fct_file {fct_path}")
    print(f"pfc_file {pfc_path}")
    print(f"flow_count {window.flow_count}")
    print(f"window_start_ns {window.start_ns}")
    print(f"window_end_ns {window.end_ns}")
    print(f"window_duration_ns {window.duration_ns}")
    print(f"pause_events {summary.pause_events}")
    print(f"resume_events {summary.resume_events}")
    print(f"duplicate_pause_events {summary.duplicate_pause_events}")
    print(f"unmatched_resume_events {summary.unmatched_resume_events}")
    print(f"open_intervals_closed {summary.open_intervals_closed}")
    print(f"observed_paused_ports {summary.observed_paused_ports}")
    print(f"peak_concurrent_paused_ports {summary.peak_concurrent_paused_ports}")
    print(f"total_pause_port_ns {summary.total_pause_port_ns}")
    print(f"pfc_duration_ratio {pfc_duration_ratio:.12g}")
    print("pfc_duration_ratio_meaning average_paused_ports_during_flow_window")
    if observed_port_pause_fraction is not None:
        print(f"observed_port_pause_fraction {observed_port_pause_fraction:.12g}")
        print(f"observed_port_pause_percent {observed_port_pause_fraction * 100.0:.6f}%")
    if normalized_port_count is not None and network_port_pause_fraction is not None:
        print(f"normalized_port_count {normalized_port_count}")
        print(f"network_port_pause_fraction {network_port_pause_fraction:.12g}")
        print(f"network_port_pause_percent {network_port_pause_fraction * 100.0:.6f}%")


if __name__ == "__main__":
    main()
