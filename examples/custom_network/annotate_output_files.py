#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path


NOTES = {
    "fct.txt": [
        "# columns:",
        "# sip_hex dip_hex src_id dst_id sport dport payload_bytes start_time_ns fct_ns standalone_fct_ns throughput_gbps",
        "# standalone_fct_ns is based on pairRtt + wire_bytes / pairBw.",
        "# throughput_gbps is wire_bytes * 8 / fct_ns.",
    ],
    "pfc.txt": [
        "# columns:",
        "# time_ns node_id node_type if_index type",
        "# type: 1=PFC pause, 0=PFC resume.",
    ],
    "qlen.txt": [
        "# row format:",
        "# time <time_ns> <switch_id> repeated pairs: j <if_index> <egress_queue_bytes>",
        "# rows are emitted only when a monitored switch has at least one nonzero queue.",
    ],
    "mix.tr": [
        "# note:",
        "# trace output is empty when ENABLE_TRACE=0; nonempty binary traces are left unmodified.",
    ],
    "run.log": [
        "# note:",
        "# stdout/stderr captured from the ASTRA-sim ns-3 run.",
    ],
    "throughput_summary.txt": [
        "# columns:",
        "# metric value unit",
        "# aggregate_payload_throughput_gbps = sum(payload_bytes) * 8 / makespan_ns.",
        "# flow_throughput_gbps metrics come from fct.txt column 11 and include packet headers.",
    ],
}


def is_binary(path: Path) -> bool:
    data = path.read_bytes()[:4096]
    return b"\0" in data


def append_notes(path: Path, notes: list[str]) -> bool:
    if path.exists() and path.stat().st_size > 0 and is_binary(path):
        return False
    existing = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    marker = notes[0]
    if marker in existing:
        return False
    suffix = "" if not existing or existing.endswith("\n") else "\n"
    path.write_text(existing + suffix + "\n".join(notes) + "\n", encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Append column notes to custom ns-3 output files.")
    parser.add_argument("--output-dir", required=True, help="Directory under ns-3 scratch/output")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    changed = []
    skipped = []
    for filename, notes in NOTES.items():
        path = output_dir / filename
        if append_notes(path, notes):
            changed.append(filename)
        else:
            skipped.append(filename)
    print(f"annotated: {', '.join(changed) if changed else 'none'}")
    print(f"skipped: {', '.join(skipped) if skipped else 'none'}")


if __name__ == "__main__":
    main()
