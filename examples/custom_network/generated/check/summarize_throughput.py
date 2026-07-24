#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
from statistics import mean


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    frac = rank - lower
    return ordered[lower] * (1.0 - frac) + ordered[upper] * frac


def parse_fct(path: Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    if not path.is_file():
        return rows
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 11:
            raise ValueError(f"{path}:{line_number}: expected at least 11 columns")
        payload_bytes = int(parts[6])
        start_time_ns = int(parts[7])
        fct_ns = int(parts[8])
        standalone_fct_ns = int(parts[9])
        throughput_gbps = float(parts[10])
        rows.append(
            {
                "payload_bytes": payload_bytes,
                "start_time_ns": start_time_ns,
                "fct_ns": fct_ns,
                "finish_time_ns": start_time_ns + fct_ns,
                "standalone_fct_ns": standalone_fct_ns,
                "throughput_gbps": throughput_gbps,
            }
        )
    return rows


def write_summary(rows: list[dict[str, float]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# columns:",
        "# metric value unit",
        "# aggregate_payload_throughput_gbps = sum(payload_bytes) * 8 / makespan_ns.",
        "# flow_throughput_gbps metrics come from fct.txt column 11 and include packet headers.",
        "# makespan_ns = max(start_time_ns + fct_ns) - min(start_time_ns).",
    ]
    if not rows:
        lines.append("completed_flows 0 count")
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    first_start = min(row["start_time_ns"] for row in rows)
    last_finish = max(row["finish_time_ns"] for row in rows)
    makespan_ns = max(last_finish - first_start, 1)
    payload_bytes = sum(row["payload_bytes"] for row in rows)
    throughputs = [row["throughput_gbps"] for row in rows]
    fcts = [row["fct_ns"] for row in rows]

    metrics = [
        ("completed_flows", len(rows), "count"),
        ("payload_bytes", payload_bytes, "bytes"),
        ("first_start_time_ns", int(first_start), "ns"),
        ("last_finish_time_ns", int(last_finish), "ns"),
        ("makespan_ns", int(makespan_ns), "ns"),
        ("aggregate_payload_throughput_gbps", payload_bytes * 8 / makespan_ns, "Gbps"),
        ("mean_flow_throughput_gbps", mean(throughputs), "Gbps"),
        ("p50_flow_throughput_gbps", percentile(throughputs, 0.50), "Gbps"),
        ("p95_flow_throughput_gbps", percentile(throughputs, 0.95), "Gbps"),
        ("max_flow_throughput_gbps", max(throughputs), "Gbps"),
        ("mean_fct_ns", mean(fcts), "ns"),
        ("p95_fct_ns", percentile(fcts, 0.95), "ns"),
        ("max_fct_ns", max(fcts), "ns"),
    ]
    for metric, value, unit in metrics:
        if isinstance(value, float):
            lines.append(f"{metric} {value:.6f} {unit}")
        else:
            lines.append(f"{metric} {value} {unit}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize ns-3 FCT throughput output.")
    parser.add_argument("--fct-file", required=True, help="Path to fct.txt")
    parser.add_argument("--output", required=True, help="Path to throughput_summary.txt")
    args = parser.parse_args()

    rows = parse_fct(Path(args.fct_file))
    write_summary(rows, Path(args.output))
    print(f"wrote {args.output} from {len(rows)} completed flows")


if __name__ == "__main__":
    main()
