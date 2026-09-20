#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


FIELD_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)")
ARN_TYPES = {
    0: "REMOTE_ARN",
    1: "REMOTE_CLEAR",
    2: "REMOTE_PERIOD",
    3: "LOCAL_ARN",
    4: "LOCAL_CLEAR",
}
REMOTE_TYPES = {0, 2}


@dataclass(frozen=True)
class ArnKey:
    event_ts: int
    arn_src: int
    arn_dst: int
    arn_sport: int
    arn_dport: int
    arn_type: int


def parse_value(value: str) -> int | str:
    if value in {"true", "True"}:
        return 1
    if value in {"false", "False"}:
        return 0
    try:
        return int(value)
    except ValueError:
        return value


def parse_record(line: str) -> tuple[str, dict[str, int | str]] | None:
    match = re.search(r"\[ARN\]\[([^\]]+)\]", line)
    if not match:
        return None
    fields = {key: parse_value(value) for key, value in FIELD_RE.findall(line)}
    return match.group(1), fields


def build_key(fields: dict[str, int | str], timestamp_field: str) -> ArnKey | None:
    required = [timestamp_field, "arn_src", "arn_dst", "arn_sport", "arn_dport", "type"]
    if any(name not in fields for name in required):
        return None
    return ArnKey(
        event_ts=int(fields[timestamp_field]),
        arn_src=int(fields["arn_src"]),
        arn_dst=int(fields["arn_dst"]),
        arn_sport=int(fields["arn_sport"]),
        arn_dport=int(fields["arn_dport"]),
        arn_type=int(fields["type"]),
    )


def summarize(records: list[dict[str, int | str]], value_field: str) -> str:
    values = [int(record[value_field]) for record in records if value_field in record]
    if not values:
        return "n/a"
    return f"min={min(values)} avg={mean(values):.0f} max={max(values)}"


def format_top(counter: Counter, top: int) -> list[str]:
    if not counter:
        return ["  none"]
    return [f"  {key}: {value}" for key, value in counter.most_common(top)]


def analyze(lines: list[str], top: int) -> str:
    sends: list[dict[str, int | str]] = []
    receives: list[dict[str, int | str]] = []
    routes: list[dict[str, int | str]] = []
    skipped: list[dict[str, int | str]] = []

    for line in lines:
        parsed = parse_record(line)
        if parsed is None:
            continue
        kind, fields = parsed
        if kind == "send":
            sends.append(fields)
        elif kind == "source-leaf-read":
            receives.append(fields)
        elif kind == "glb-route":
            routes.append(fields)
        elif kind == "send-skip":
            skipped.append(fields)

    remote_sends = [record for record in sends if int(record.get("type", -1)) in REMOTE_TYPES]
    remote_receives = [record for record in receives if int(record.get("type", -1)) in REMOTE_TYPES]

    send_by_key: dict[ArnKey, list[dict[str, int | str]]] = defaultdict(list)
    for record in remote_sends:
        key = build_key(record, "time_ns")
        if key is not None:
            send_by_key[key].append(record)

    matched = 0
    unmatched = 0
    path_mismatch = 0
    leaf_mismatch = 0
    recv_path_counter: Counter[str] = Counter()
    origin_counter: Counter[str] = Counter()
    arninfo_counter: Counter[str] = Counter()
    origin_records: dict[str, list[dict[str, int | str]]] = defaultdict(list)
    receive_delays_ns: list[int] = []
    first_send_by_path: dict[int, int] = {}
    first_receive_by_path: dict[int, int] = {}

    for record in remote_sends:
        origin = str(record.get("switch", "unknown"))
        src_leaf = record.get("arn_dst", "unknown")
        dst_leaf = record.get("arn_src", "unknown")
        path = record.get("arn_sport", "unknown")
        out_dev = record.get("arn_dport", "unknown")
        origin_counter[f"origin_spine={origin} srcLeaf={src_leaf} dstLeaf={dst_leaf}"] += 1
        arninfo_counter[
            f"origin_spine={origin} srcLeaf={src_leaf} dstLeaf={dst_leaf} "
            f"path={path} outDev={out_dev} qLevel={record.get('q_level', 'n/a')} "
            f"loadLevel={record.get('load_level', 'n/a')} type={ARN_TYPES.get(int(record.get('type', -1)), record.get('type', 'n/a'))}"
        ] += 1
        origin_records[origin].append(record)
        path_int = int(record.get("arn_sport", -1))
        if path_int >= 0:
            first_send_by_path.setdefault(path_int, int(record.get("time_ns", 0)))

    for record in remote_receives:
        key = build_key(record, "event_ts")
        if key is None or key not in send_by_key:
            unmatched += 1
        else:
            matched += 1
            receive_delays_ns.append(int(record.get("time_ns", 0)) - int(record.get("event_ts", 0)))
        congested_path = int(record.get("congestedPath", -1))
        arn_sport = int(record.get("arn_sport", -2))
        if congested_path != arn_sport:
            path_mismatch += 1
        switch = int(record.get("switch", -1))
        arn_dst = int(record.get("arn_dst", -2))
        if switch != arn_dst:
            leaf_mismatch += 1
        recv_path_counter[
            f"srcLeaf={record.get('switch', 'unknown')} dstLeaf={record.get('arn_src', 'unknown')} "
            f"congestedPath={record.get('congestedPath', 'unknown')} "
            f"qLevel={record.get('q_level', 'n/a')} loadLevel={record.get('load_level', 'n/a')}"
        ] += 1
        if congested_path >= 0:
            first_receive_by_path.setdefault(congested_path, int(record.get("time_ns", 0)))

    remote_route_counter: Counter[str] = Counter()
    route_times: list[int] = []
    for record in routes:
        if "time_ns" in record:
            route_times.append(int(record["time_ns"]))
        remote_q = int(record.get("remote_q", 0))
        remote_load = int(record.get("remote_load", 0))
        if remote_q == 0 and remote_load == 0:
            continue
        remote_route_counter[
            f"switch={record.get('switch', 'unknown')} dstLeaf={record.get('dstLeaf', 'unknown')} "
            f"nexthop={record.get('nexthop', 'unknown')} remoteQ={remote_q} remoteLoad={remote_load}"
        ] += 1

    output: list[str] = []
    output.append("ARN trace summary")
    output.append(f"remote_sends={len(remote_sends)} remote_receives={len(remote_receives)}")
    output.append(
        f"matched_receives={matched} unmatched_receives={unmatched} "
        f"path_mismatches={path_mismatch} leaf_mismatches={leaf_mismatch}"
    )
    if receive_delays_ns:
        output.append(
            f"receive_delay_ns min={min(receive_delays_ns)} "
            f"avg={mean(receive_delays_ns):.0f} max={max(receive_delays_ns)}"
        )
    if route_times:
        output.append(f"glb_route_time_ns min={min(route_times)} max={max(route_times)}")
    output.append(f"send_skips={len(skipped)} glb_remote_route_reads={sum(remote_route_counter.values())}")
    if first_send_by_path:
        output.append("first_remote_arn_by_path")
        for path in sorted(first_send_by_path):
            first_send = first_send_by_path[path]
            first_receive = first_receive_by_path.get(path)
            if first_receive is None:
                output.append(f"  path={path} first_send_ns={first_send} first_receive_ns=n/a")
            else:
                output.append(
                    f"  path={path} first_send_ns={first_send} "
                    f"first_receive_ns={first_receive} delay_ns={first_receive - first_send}"
                )
    output.append("")
    output.append("Remote ARN origins")
    output.extend(format_top(origin_counter, top))
    for origin, records in sorted(origin_records.items(), key=lambda item: int(item[0]) if item[0].isdigit() else 999999):
        output.append(f"  origin_spine={origin} q_len_{summarize(records, 'q_len')}")
    output.append("")
    output.append("Marked congestion paths received by source leaves")
    output.extend(format_top(recv_path_counter, top))
    output.append("")
    output.append("ARN info carried by remote sends")
    output.extend(format_top(arninfo_counter, top))
    output.append("")
    output.append("GLB route reads using remote quality")
    output.extend(format_top(remote_route_counter, top))
    return "\n".join(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize ARN debug traces from ns-3 stdout.")
    parser.add_argument("trace_log", nargs="?", help="ns-3 stdout log containing [ARN] trace lines; stdin if omitted")
    parser.add_argument("--top", type=int, default=20, help="number of top grouped records to print")
    args = parser.parse_args()

    if args.trace_log:
        lines = Path(args.trace_log).read_text(encoding="utf-8", errors="replace").splitlines()
    else:
        lines = sys.stdin.read().splitlines()
    print(analyze(lines, args.top))


if __name__ == "__main__":
    main()
