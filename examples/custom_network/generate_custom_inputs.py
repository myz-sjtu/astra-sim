#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
NS3_ROOT = REPO_ROOT / "extern" / "network_backend" / "ns-3"
CHAKRA_PROTO_DIR = REPO_ROOT / "extern" / "graph_frontend" / "chakra" / "schema" / "protobuf"
sys.path.insert(0, str(REPO_ROOT))


def ensure_chakra_python_proto() -> None:
    generated_proto = CHAKRA_PROTO_DIR / "et_def_pb2.py"
    if generated_proto.is_file():
        return

    proto = CHAKRA_PROTO_DIR / "et_def.proto"
    if not proto.is_file():
        raise RuntimeError(f"missing Chakra protobuf schema: {proto}")

    try:
        subprocess.run(
            [
                "protoc",
                "et_def.proto",
                f"--proto_path={CHAKRA_PROTO_DIR}",
                f"--python_out={CHAKRA_PROTO_DIR}",
            ],
            check=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            "missing Chakra Python protobuf module et_def_pb2.py and protoc is "
            "not available; run this inside the astra-sim Docker image or install protoc"
        ) from error
    except subprocess.CalledProcessError as error:
        raise RuntimeError(
            f"failed to generate Chakra Python protobuf module from {proto}"
        ) from error


ensure_chakra_python_proto()

from extern.graph_frontend.chakra.schema.protobuf.et_def_pb2 import (  # noqa: E402
    COMP_NODE,
    COMM_RECV_NODE,
    COMM_SEND_NODE,
    GlobalMetadata,
)
from extern.graph_frontend.chakra.schema.protobuf.et_def_pb2 import (  # noqa: E402
    AttributeProto as ChakraAttr,
)
from extern.graph_frontend.chakra.schema.protobuf.et_def_pb2 import (  # noqa: E402
    Node as ChakraNode,
)
from extern.graph_frontend.chakra.src.third_party.utils.protolib import (  # noqa: E402
    encodeMessage as encode_message,
)


MAX_MESSAGE_BYTES = (1 << 31) - 1
MAX_UINT32 = (1 << 32) - 1
RATE_UNITS = {
    "bps": 1,
    "Kbps": 1_000,
    "Mbps": 1_000_000,
    "Gbps": 1_000_000_000,
    "Tbps": 1_000_000_000_000,
}
NS_PER_SECOND = 1_000_000_000
NS_PER_MICROSECOND = 1_000


class ScenarioError(ValueError):
    pass


def resolve_repo_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def ns3_relative(path: Path) -> str:
    return Path(os.path.relpath(path.resolve(), NS3_ROOT)).as_posix()


def require_int(value: Any, field: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ScenarioError(f"{field} must be an integer")
    if value < minimum:
        raise ScenarioError(f"{field} must be >= {minimum}")
    return value


def require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ScenarioError(f"{field} must be a boolean")
    return value


def parse_start_time_ns(raw_flow: dict[str, Any], field_prefix: str) -> int:
    has_ns = "start_time_ns" in raw_flow
    has_s = "start_time_s" in raw_flow
    has_legacy = "start_time" in raw_flow
    if sum([has_ns, has_s, has_legacy]) > 1:
        raise ScenarioError(
            f"{field_prefix} may define only one of start_time_ns, start_time_s, start_time"
        )
    if has_ns:
        return require_int(raw_flow["start_time_ns"], f"{field_prefix}.start_time_ns")
    if has_s or has_legacy:
        key = "start_time_s" if has_s else "start_time"
        value = raw_flow[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ScenarioError(f"{field_prefix}.{key} must be numeric seconds")
        if value < 0:
            raise ScenarioError(f"{field_prefix}.{key} must be >= 0")
        return int(round(float(value) * NS_PER_SECOND))
    return 0


def format_seconds_from_ns(start_time_ns: int) -> str:
    if start_time_ns % NS_PER_SECOND == 0:
        return str(start_time_ns // NS_PER_SECOND)
    return f"{start_time_ns / NS_PER_SECOND:.9f}".rstrip("0").rstrip(".")


def parse_data_rate(value: str, field: str) -> int:
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([KMGT]?bps)", value)
    if not match or match.group(2) not in RATE_UNITS:
        raise ScenarioError(f"{field} has unsupported data rate: {value}")
    bps = float(match.group(1)) * RATE_UNITS[match.group(2)]
    if not bps.is_integer() or bps <= 0:
        raise ScenarioError(f"{field} must resolve to a positive integer bps value")
    return int(bps)


def parse_level_config(value: Any, field: str) -> list[int] | None:
    if value is None:
        return None
    if not isinstance(value, list) or not value:
        raise ScenarioError(f"{field} must be a non-empty integer list")
    levels = [require_int(item, f"{field}[{index}]") for index, item in enumerate(value)]
    if levels != sorted(levels):
        raise ScenarioError(f"{field} must be sorted ascending")
    return levels


def normalize_explicit_flows(
    raw_flows: Any,
    num_npus: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not isinstance(raw_flows, list):
        raise ScenarioError("flows must be a list")

    flows: list[dict[str, Any]] = []
    seen_flow_keys: set[tuple[int, int, int]] = set()
    for index, raw_flow in enumerate(raw_flows):
        if not isinstance(raw_flow, dict):
            raise ScenarioError(f"flows[{index}] must be an object")
        src = require_int(raw_flow.get("src"), f"flows[{index}].src")
        dst = require_int(raw_flow.get("dst"), f"flows[{index}].dst")
        size = require_int(raw_flow.get("bytes"), f"flows[{index}].bytes", 1)
        tag = require_int(raw_flow.get("tag", index + 1), f"flows[{index}].tag")
        start_time_ns = parse_start_time_ns(raw_flow, f"flows[{index}]")
        fwd_mode = raw_flow.get("strategy", raw_flow.get("fwd_mode"))
        if fwd_mode is not None:
            fwd_mode = require_int(fwd_mode, f"flows[{index}].strategy")
            if fwd_mode not in (0, 1):
                raise ScenarioError(f"flows[{index}].strategy must be 0 or 1")

        if src >= num_npus or dst >= num_npus:
            raise ScenarioError(f"flows[{index}] endpoints must be server IDs below num_npus")
        if src == dst:
            raise ScenarioError(f"flows[{index}] must use different source and destination")
        if size > MAX_MESSAGE_BYTES:
            raise ScenarioError(
                f"flows[{index}].bytes exceeds the current MsgEvent limit of "
                f"{MAX_MESSAGE_BYTES}"
            )
        if tag > MAX_UINT32:
            raise ScenarioError(f"flows[{index}].tag exceeds uint32")

        flow_key = (src, dst, tag)
        if flow_key in seen_flow_keys:
            raise ScenarioError(
                f"flows[{index}] duplicates the (src, dst, tag) key {flow_key}"
            )
        seen_flow_keys.add(flow_key)
        flows.append(
            {
                "phase": 0,
                "phase_name": "explicit",
                "phase_flow_index": index + 1,
                "offset": abs(dst - src),
                "direction": "explicit",
                "src": src,
                "dst": dst,
                "bytes": size,
                "tag": tag,
                "start_time_ns": start_time_ns,
                "fwd_mode": fwd_mode,
            }
        )

    return flows, {
        "pattern": "explicit_flows",
        "phase_sync": "none",
        "include_reverse": False,
    }


def expand_half_doubling_traffic(
    raw_traffic: Any,
    num_npus: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not isinstance(raw_traffic, dict):
        raise ScenarioError("traffic must be an object")
    pattern = raw_traffic.get("pattern")
    if pattern != "half_doubling_allreduce":
        raise ScenarioError(f"unsupported traffic.pattern: {pattern}")

    raw_offsets = raw_traffic.get("offsets")
    if not isinstance(raw_offsets, list) or not raw_offsets:
        raise ScenarioError("traffic.offsets must be a non-empty list")
    offsets = [
        require_int(value, f"traffic.offsets[{index}]", 1)
        for index, value in enumerate(raw_offsets)
    ]
    if len(set(offsets)) != len(offsets):
        raise ScenarioError("traffic.offsets must be unique")
    if offsets[0] * 2 != num_npus:
        raise ScenarioError("traffic.offsets[0] must equal num_npus / 2")
    for previous, current in zip(offsets, offsets[1:]):
        if previous != current * 2:
            raise ScenarioError("traffic.offsets must halve at every phase")
    for index, offset in enumerate(offsets):
        if num_npus % (2 * offset) != 0:
            raise ScenarioError(
                f"traffic.offsets[{index}] does not evenly divide num_npus"
            )

    bytes_per_flow = require_int(
        raw_traffic.get("bytes_per_flow"),
        "traffic.bytes_per_flow",
        1,
    )
    if bytes_per_flow > MAX_MESSAGE_BYTES:
        raise ScenarioError(
            "traffic.bytes_per_flow exceeds the current MsgEvent limit of "
            f"{MAX_MESSAGE_BYTES}"
        )

    include_reverse = require_bool(
        raw_traffic.get("include_reverse", True),
        "traffic.include_reverse",
    )
    phase_sync = raw_traffic.get("phase_sync", "per_rank")
    if phase_sync != "per_rank":
        raise ScenarioError("traffic.phase_sync must be 'per_rank'")

    phase_specs = [(offset, False) for offset in offsets]
    if include_reverse:
        phase_specs.extend((offset, True) for offset in reversed(offsets))

    flows: list[dict[str, Any]] = []
    for phase_number, (offset, reverse) in enumerate(phase_specs, start=1):
        phase_flow_index = 0
        participants: set[int] = set()
        direction = "upper_to_lower" if reverse else "lower_to_upper"
        phase_name = f"phase_{phase_number}_{direction}_offset_{offset}"

        for group_base in range(0, num_npus, 2 * offset):
            for pair_index in range(offset):
                lower = group_base + pair_index
                upper = lower + offset
                src, dst = (upper, lower) if reverse else (lower, upper)
                phase_flow_index += 1
                tag = phase_number * 1000 + phase_flow_index
                if tag > MAX_UINT32:
                    raise ScenarioError("generated traffic tag exceeds uint32")
                flows.append(
                    {
                        "phase": phase_number,
                        "phase_name": phase_name,
                        "phase_flow_index": phase_flow_index,
                        "offset": offset,
                        "direction": direction,
                        "src": src,
                        "dst": dst,
                        "bytes": bytes_per_flow,
                        "tag": tag,
                        "start_time_ns": 0,
                        "fwd_mode": None,
                    }
                )
                participants.add(src)
                participants.add(dst)

        if phase_flow_index != num_npus // 2 or len(participants) != num_npus:
            raise ScenarioError(
                f"generated phase {phase_number} does not cover every rank exactly once"
            )

    return flows, {
        "pattern": pattern,
        "offsets": offsets,
        "bytes_per_flow": bytes_per_flow,
        "include_reverse": include_reverse,
        "phase_sync": phase_sync,
    }


def normalize_scenario(raw: dict[str, Any]) -> dict[str, Any]:
    name = raw.get("name", "custom_network")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise ScenarioError("name may only contain letters, numbers, '.', '_' and '-'")

    num_npus = require_int(raw.get("num_npus"), "num_npus", 1)
    switches = raw.get("switches")
    if not isinstance(switches, list):
        raise ScenarioError("switches must be a list of node IDs")
    switches = [require_int(value, "switch ID", num_npus) for value in switches]
    if len(set(switches)) != len(switches):
        raise ScenarioError("switch IDs must be unique")

    leaf_switches = raw.get("leaf_switches")
    spine_switches = raw.get("spine_switches")
    if leaf_switches is None and spine_switches is None:
        leaf_switches = switches
        spine_switches = []
    elif leaf_switches is None or spine_switches is None:
        raise ScenarioError("leaf_switches and spine_switches must be defined together")
    elif not isinstance(leaf_switches, list) or not isinstance(spine_switches, list):
        raise ScenarioError("leaf_switches and spine_switches must be lists")
    else:
        leaf_switches = [require_int(value, "leaf switch ID", num_npus) for value in leaf_switches]
        spine_switches = [require_int(value, "spine switch ID", num_npus) for value in spine_switches]
    if sorted(leaf_switches + spine_switches) != sorted(switches):
        raise ScenarioError("leaf_switches plus spine_switches must exactly match switches")
    if set(leaf_switches) & set(spine_switches):
        raise ScenarioError("leaf_switches and spine_switches must not overlap")

    expected_switches = list(range(num_npus, num_npus + len(switches)))
    if sorted(switches) != expected_switches:
        raise ScenarioError(
            "server IDs must be 0..num_npus-1 and switch IDs must be contiguous "
            "immediately after the server IDs"
        )

    node_count = num_npus + len(switches)
    link_defaults = raw.get("link_defaults", {})
    if not isinstance(link_defaults, dict):
        raise ScenarioError("link_defaults must be an object")
    default_bandwidth = str(link_defaults.get("bandwidth", "100Gbps"))
    default_latency = str(link_defaults.get("latency", "1000ns"))
    default_error_rate = float(link_defaults.get("error_rate", 0.0))

    raw_links = raw.get("links")
    if not isinstance(raw_links, list) or not raw_links:
        raise ScenarioError("links must be a non-empty list")

    links: list[dict[str, Any]] = []
    adjacency: dict[int, set[int]] = defaultdict(set)
    for index, raw_link in enumerate(raw_links):
        if not isinstance(raw_link, dict):
            raise ScenarioError(f"links[{index}] must be an object")
        src = require_int(raw_link.get("src"), f"links[{index}].src")
        dst = require_int(raw_link.get("dst"), f"links[{index}].dst")
        if src >= node_count or dst >= node_count:
            raise ScenarioError(f"links[{index}] references a node outside 0..{node_count - 1}")
        if src == dst:
            raise ScenarioError(f"links[{index}] cannot connect a node to itself")

        bandwidth = str(raw_link.get("bandwidth", default_bandwidth))
        latency = str(raw_link.get("latency", default_latency))
        error_rate = float(raw_link.get("error_rate", default_error_rate))
        count = require_int(raw_link.get("count", 1), f"links[{index}].count", 1)
        if not bandwidth or not latency or error_rate < 0:
            raise ScenarioError(f"links[{index}] has invalid link parameters")

        for _ in range(count):
            links.append(
                {
                    "src": src,
                    "dst": dst,
                    "bandwidth": bandwidth,
                    "latency": latency,
                    "error_rate": error_rate,
                }
            )
        adjacency[src].add(dst)
        adjacency[dst].add(src)

    visited = {0}
    queue = deque([0])
    while queue:
        node = queue.popleft()
        for neighbor in adjacency[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    if len(visited) != node_count:
        missing = sorted(set(range(node_count)) - visited)
        raise ScenarioError(f"topology is disconnected; unreachable nodes: {missing}")

    has_flows = "flows" in raw
    has_traffic = "traffic" in raw
    if has_flows == has_traffic:
        raise ScenarioError("scenario must define exactly one of 'flows' or 'traffic'")
    if has_flows:
        flows, traffic = normalize_explicit_flows(raw["flows"], num_npus)
    else:
        flows, traffic = expand_half_doubling_traffic(raw["traffic"], num_npus)

    network = raw.get("network", {})
    if not isinstance(network, dict):
        raise ScenarioError("network must be an object")
    default_fwd_mode = require_int(
        network.get("default_fwd_mode", 0), "network.default_fwd_mode"
    )
    if default_fwd_mode not in (0, 1):
        raise ScenarioError("network.default_fwd_mode must be 0 or 1")
    flow_strategy = require_int(
        network.get("flow_strategy", 0), "network.flow_strategy"
    )
    if flow_strategy != 0:
        raise ScenarioError("network.flow_strategy currently supports only 0")
    packet_strategy = require_int(
        network.get("packet_strategy", 0), "network.packet_strategy"
    )
    enable_arn = require_int(network.get("enable_arn", 0), "network.enable_arn")
    if enable_arn not in (0, 1):
        raise ScenarioError("network.enable_arn must be 0 or 1")
    arn_packet_strategy = require_int(
        network.get("arn_packet_strategy", 0),
        "network.arn_packet_strategy",
    )
    if packet_strategy not in (0, 1, 2):
        raise ScenarioError("network.packet_strategy must be 0, 1, or 2")
    if arn_packet_strategy not in (0, 1, 2, 3):
        raise ScenarioError("network.arn_packet_strategy must be 0, 1, 2, or 3")
    arn_scale_size = require_int(
        network.get("arn_scale_size", 4), "network.arn_scale_size", 1
    )
    arn_interval_ns = require_int(
        network.get("arn_interval_ns", 10_000), "network.arn_interval_ns", 1
    )
    arn_congestion_qlen = require_int(
        network.get("arn_congestion_qlen", 5_000_000),
        "network.arn_congestion_qlen",
        1,
    )
    q_level = parse_level_config(network.get("q_level"), "network.q_level")
    load_level = parse_level_config(network.get("load_level"), "network.load_level")
    for flow in flows:
        if flow["fwd_mode"] is None:
            flow["fwd_mode"] = default_fwd_mode

    enable_trace = require_int(network.get("enable_trace", 0), "network.enable_trace")
    if enable_trace not in (0, 1):
        raise ScenarioError("network.enable_trace must be 0 or 1")
    qlen_mon_start_ns = require_int(
        network.get("qlen_mon_start_ns", 0), "network.qlen_mon_start_ns"
    )
    qlen_mon_end_ns = require_int(
        network.get("qlen_mon_end_ns", 2_000_000), "network.qlen_mon_end_ns"
    )
    qlen_mon_interval_ns = require_int(
        network.get("qlen_mon_interval_ns", 100_000),
        "network.qlen_mon_interval_ns",
        1,
    )
    if qlen_mon_end_ns < qlen_mon_start_ns:
        raise ScenarioError("network.qlen_mon_end_ns must be >= qlen_mon_start_ns")

    ecn_thresholds = None
    raw_ecn_thresholds = network.get("ecn_thresholds")
    if raw_ecn_thresholds is not None:
        if not isinstance(raw_ecn_thresholds, list) or not raw_ecn_thresholds:
            raise ScenarioError("network.ecn_thresholds must be a non-empty list")
        ecn_thresholds = []
        seen_rates: set[int] = set()
        for index, threshold in enumerate(raw_ecn_thresholds):
            if not isinstance(threshold, dict):
                raise ScenarioError(f"network.ecn_thresholds[{index}] must be an object")
            bandwidth = str(threshold.get("bandwidth", ""))
            rate_bps = parse_data_rate(
                bandwidth, f"network.ecn_thresholds[{index}].bandwidth"
            )
            if rate_bps in seen_rates:
                raise ScenarioError(f"duplicate ECN threshold for {bandwidth}")
            seen_rates.add(rate_bps)
            ecn_thresholds.append(
                {
                    "rate_bps": rate_bps,
                    "kmin": require_int(
                        threshold.get("kmin"),
                        f"network.ecn_thresholds[{index}].kmin",
                    ),
                    "kmax": require_int(
                        threshold.get("kmax"),
                        f"network.ecn_thresholds[{index}].kmax",
                    ),
                    "pmax": float(threshold.get("pmax", 0.2)),
                }
            )

        link_rates = {
            parse_data_rate(link["bandwidth"], "link bandwidth") for link in links
        }
        threshold_rates = {entry["rate_bps"] for entry in ecn_thresholds}
        missing_rates = sorted(link_rates - threshold_rates)
        if missing_rates:
            raise ScenarioError(
                f"network.ecn_thresholds is missing link rates: {missing_rates}"
            )
        ecn_thresholds.sort(key=lambda entry: entry["rate_bps"])

    return {
        "name": name,
        "num_npus": num_npus,
        "node_count": node_count,
        "switches": sorted(switches),
        "leaf_switches": leaf_switches,
        "spine_switches": spine_switches,
        "links": links,
        "flows": flows,
        "traffic": traffic,
        "network": {
            "default_fwd_mode": default_fwd_mode,
            "flow_strategy": flow_strategy,
            "packet_strategy": packet_strategy,
            "arn_packet_strategy": arn_packet_strategy,
            "arn_scale_size": arn_scale_size,
            "enable_arn": enable_arn,
            "arn_interval_ns": arn_interval_ns,
            "arn_congestion_qlen": arn_congestion_qlen,
            "q_level": q_level,
            "load_level": load_level,
            "enable_trace": enable_trace,
            "qlen_mon_start_ns": qlen_mon_start_ns,
            "qlen_mon_end_ns": qlen_mon_end_ns,
            "qlen_mon_interval_ns": qlen_mon_interval_ns,
            "ecn_thresholds": ecn_thresholds,
        },
    }


def write_topology(scenario: dict[str, Any], output_path: Path) -> None:
    lines = [
        (
            f"{scenario['node_count']} {len(scenario['leaf_switches'])} "
            f"{len(scenario['spine_switches'])} {len(scenario['links'])}"
        ),
        " ".join(str(switch_id) for switch_id in scenario["leaf_switches"]),
        " ".join(str(switch_id) for switch_id in scenario["spine_switches"]),
    ]
    for link in scenario["links"]:
        lines.append(
            f"{link['src']} {link['dst']} {link['bandwidth']} "
            f"{link['latency']} {link['error_rate']}"
        )
    lines.extend(
        [
            "",
            "# columns:",
            "# header: node_count leaf_switch_count spine_switch_count link_count",
            "# next line: leaf switch node IDs",
            "# next line: spine switch node IDs",
            "# link rows: src_node dst_node bandwidth latency error_rate",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_flow_file(scenario: dict[str, Any], output_path: Path) -> None:
    lines = [str(len(scenario["flows"]))]
    for flow in scenario["flows"]:
        lines.append(
            f"{flow['src']} {flow['dst']} 3 100 {flow['bytes']} "
            f"{format_seconds_from_ns(flow['start_time_ns'])} {flow['fwd_mode']} {flow['tag']}"
        )
    lines.extend(
        [
            "",
            "# columns:",
            "# first row: flow_count",
            "# flow rows: src dst priority_group dst_port payload_bytes start_time_seconds strategy comm_tag",
            "# strategy: 0=flow ECMP, 1=packet spray",
            "# comm_tag explicitly identifies the ASTRA-sim message for start/strategy overrides.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_comm_node(
    node_id: int,
    node_type: int,
    flow_index: int,
    flow: dict[str, Any],
    parent_node_id: int | None,
) -> ChakraNode:
    direction = "send" if node_type == COMM_SEND_NODE else "recv"
    node = ChakraNode()
    node.id = node_id
    node.name = (
        f"{direction}_{flow['phase_name']}_flow_{flow_index}_"
        f"{flow['src']}_to_{flow['dst']}_{flow['bytes']}B"
    )
    node.type = node_type
    if parent_node_id is not None:
        node.data_deps.append(parent_node_id)
    node.attr.extend(
        [
            ChakraAttr(name="is_cpu_op", bool_val=False),
            ChakraAttr(name="comm_src", uint32_val=flow["src"]),
            ChakraAttr(name="comm_dst", uint32_val=flow["dst"]),
            ChakraAttr(name="comm_size", uint64_val=flow["bytes"]),
            ChakraAttr(name="comm_tag", uint32_val=flow["tag"]),
            ChakraAttr(name="comm_start_time_ns", uint64_val=flow["start_time_ns"]),
            ChakraAttr(name="comm_fwd_mode", uint32_val=flow["fwd_mode"]),
        ]
    )
    return node


def write_workloads(scenario: dict[str, Any], workload_dir: Path) -> Path:
    workload_dir.mkdir(parents=True, exist_ok=True)
    workload_prefix = workload_dir / "custom_traffic"
    for stale_file in workload_dir.glob("custom_traffic.*.et"):
        stale_file.unlink()

    nodes_by_rank: dict[int, list[ChakraNode]] = {
        rank: [] for rank in range(scenario["num_npus"])
    }
    next_node_id = [0] * scenario["num_npus"]
    last_node_id: list[int | None] = [None] * scenario["num_npus"]
    chain_phases = scenario["traffic"]["phase_sync"] == "per_rank"

    for flow_index, flow in enumerate(scenario["flows"]):
        src = flow["src"]
        dst = flow["dst"]

        send_node = make_comm_node(
            next_node_id[src],
            COMM_SEND_NODE,
            flow_index,
            flow,
            last_node_id[src] if chain_phases else None,
        )
        next_node_id[src] += 1
        nodes_by_rank[src].append(send_node)
        if chain_phases:
            last_node_id[src] = send_node.id

        recv_node = make_comm_node(
            next_node_id[dst],
            COMM_RECV_NODE,
            flow_index,
            flow,
            last_node_id[dst] if chain_phases else None,
        )
        next_node_id[dst] += 1
        nodes_by_rank[dst].append(recv_node)
        if chain_phases:
            last_node_id[dst] = recv_node.id

    for rank, nodes in nodes_by_rank.items():
        if not nodes:
            placeholder = ChakraNode()
            placeholder.id = 0
            placeholder.name = "empty_rank_gpu_placeholder"
            placeholder.type = COMP_NODE
            placeholder.duration_micros = 0
            # Keep idle ranks statistics-compatible with ASTRA-sim overlap
            # extraction, which only accepts GPU and COMM operator types.
            placeholder.attr.append(ChakraAttr(name="is_cpu_op", bool_val=False))
            nodes.append(placeholder)
        et_path = Path(f"{workload_prefix}.{rank}.et")
        with et_path.open("wb") as et_file:
            encode_message(et_file, GlobalMetadata(version="0.0.4"))
            for node in nodes:
                encode_message(et_file, node)

    return workload_prefix


def write_traffic_manifest(scenario: dict[str, Any], output_path: Path) -> None:
    output_path.write_text(
        json.dumps(
            {
                **scenario["traffic"],
                "flow_count": len(scenario["flows"]),
                "flows": scenario["flows"],
                "schema": {
                    "phase": "traffic phase number; 0 means explicit user flow",
                    "phase_name": "human-readable phase label",
                    "phase_flow_index": "1-based flow index inside the phase",
                    "offset": "absolute rank distance for generated traffic or abs(dst-src)",
                    "direction": "traffic direction label",
                    "src": "source rank / host node ID",
                    "dst": "destination rank / host node ID",
                    "bytes": "payload bytes",
                    "tag": "ASTRA-sim comm_tag; matches the explicit tag column in flow.txt",
                    "start_time_ns": "requested flow start time in ns",
                    "fwd_mode": "0=flow ECMP, 1=packet spray",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def rewrite_network_config(
    base_config: Path,
    output_config: Path,
    replacements: dict[str, str],
) -> None:
    seen: set[str] = set()
    output_lines: list[str] = []
    for line in base_config.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            output_lines.append("")
            continue
        key = stripped.split(maxsplit=1)[0]
        if key in replacements:
            output_lines.append(f"{key} {replacements[key]}")
            seen.add(key)
        else:
            output_lines.append(line)

    missing = sorted(set(replacements) - seen)
    if missing:
        raise ScenarioError(
            f"base network config is missing required keys: {', '.join(missing)}"
        )
    output_config.write_text("\n".join(output_lines) + "\n", encoding="utf-8")


def generate(
    scenario_path: Path,
    output_dir: Path,
    base_network_config: Path,
) -> dict[str, Any]:
    raw = json.loads(scenario_path.read_text(encoding="utf-8"))
    scenario = normalize_scenario(raw)
    output_dir.mkdir(parents=True, exist_ok=True)

    topology_path = output_dir / "topology.txt"
    logical_topology_path = output_dir / "logical_topology.json"
    flow_file_path = output_dir / "flow.txt"
    trace_path = output_dir / "trace.txt"
    network_config_path = output_dir / "network_config.txt"
    traffic_manifest_path = output_dir / "traffic_manifest.json"
    workload_prefix = write_workloads(scenario, output_dir / "workload")

    write_topology(scenario, topology_path)
    write_traffic_manifest(scenario, traffic_manifest_path)
    logical_topology_path.write_text(
        json.dumps({"logical-dims": [str(scenario["num_npus"])]}, indent=2) + "\n",
        encoding="utf-8",
    )
    write_flow_file(scenario, flow_file_path)
    trace_path.write_text(
        "0\n\n# columns:\n# first row: trace_node_count\n# following row, if any: traced node IDs\n",
        encoding="utf-8",
    )

    name = scenario["name"]
    network = scenario["network"]
    ns3_output_dir = NS3_ROOT / "scratch" / "output" / name
    ns3_output_dir.mkdir(parents=True, exist_ok=True)
    replacements = {
        "TOPOLOGY_FILE": ns3_relative(topology_path),
        "FLOW_FILE": ns3_relative(flow_file_path),
        "TRACE_FILE": ns3_relative(trace_path),
        "TRACE_OUTPUT_FILE": f"scratch/output/{name}/mix.tr",
        "FCT_OUTPUT_FILE": f"scratch/output/{name}/fct.txt",
        "PFC_OUTPUT_FILE": f"scratch/output/{name}/pfc.txt",
        "RUNTIME_OUTPUT_FILE": f"scratch/output/{name}/runtime.txt",
        "QLEN_MON_FILE": f"scratch/output/{name}/qlen.txt",
        "QLEN_MON_START": str(network["qlen_mon_start_ns"]),
        "QLEN_MON_END": str(network["qlen_mon_end_ns"]),
        "QLEN_MON_INTERVAL": str(network["qlen_mon_interval_ns"]),
        "FLOW_STRATEGY": str(network["flow_strategy"]),
        "PACKET_STRATEGY": str(network["packet_strategy"]),
        "ARN_PACKET_STRATEGY": str(network["arn_packet_strategy"]),
        "ARN_SCALE_SIZE": str(network["arn_scale_size"]),
        "DEFAULT_FWD_MODE": str(network["default_fwd_mode"]),
        "ENABLE_ARN": str(network["enable_arn"]),
        "ARN_INTERVAL": str(network["arn_interval_ns"]),
        "ARN_CONGESTION_QLEN": str(network["arn_congestion_qlen"]),
        "ENABLE_TRACE": str(network["enable_trace"]),
    }
    if network["q_level"] is not None:
        replacements["Q_LEVEL"] = (
            f"{len(network['q_level'])} " + " ".join(str(v) for v in network["q_level"])
        )
    if network["load_level"] is not None:
        replacements["LOAD_LEVEL"] = (
            f"{len(network['load_level'])} "
            + " ".join(str(v) for v in network["load_level"])
        )
    if network["ecn_thresholds"] is not None:
        thresholds = network["ecn_thresholds"]
        replacements.update(
            {
                "KMIN_MAP": f"{len(thresholds)} "
                + " ".join(
                    f"{entry['rate_bps']} {entry['kmin']}" for entry in thresholds
                ),
                "KMAX_MAP": f"{len(thresholds)} "
                + " ".join(
                    f"{entry['rate_bps']} {entry['kmax']}" for entry in thresholds
                ),
                "PMAX_MAP": f"{len(thresholds)} "
                + " ".join(
                    f"{entry['rate_bps']} {entry['pmax']}" for entry in thresholds
                ),
            }
        )
    rewrite_network_config(base_network_config, network_config_path, replacements)

    manifest = {
        "name": name,
        "num_npus": scenario["num_npus"],
        "workload_configuration": ns3_relative(workload_prefix),
        "system_configuration": ns3_relative(
            REPO_ROOT / "examples" / "system" / "native_collectives" / "Ring_4chunks.json"
        ),
        "network_configuration": ns3_relative(network_config_path),
        "remote_memory_configuration": ns3_relative(
            REPO_ROOT
            / "examples"
            / "remote_memory"
            / "analytical"
            / "no_memory_expansion.json"
        ),
        "logical_topology_configuration": ns3_relative(logical_topology_path),
        "comm_group_configuration": "empty",
        "fct_output": f"scratch/output/{name}/fct.txt",
        "runtime_output": f"scratch/output/{name}/runtime.txt",
        "output_directory": f"scratch/output/{name}",
        "annotation_command": (
            f"python3 {ns3_relative(REPO_ROOT / 'examples' / 'custom_network' / 'annotate_output_files.py')} "
            f"--output-dir {ns3_relative(ns3_output_dir)}"
        ),
        "traffic_manifest": ns3_relative(traffic_manifest_path),
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def print_run_command(manifest: dict[str, Any]) -> None:
    args = [
        f"--workload-configuration={manifest['workload_configuration']}",
        f"--system-configuration={manifest['system_configuration']}",
        f"--network-configuration={manifest['network_configuration']}",
        f"--remote-memory-configuration={manifest['remote_memory_configuration']}",
        f"--logical-topology-configuration={manifest['logical_topology_configuration']}",
        f"--comm-group-configuration={manifest['comm_group_configuration']}",
    ]
    print("Generated custom topology and Chakra workloads.")
    print(f"Run from {NS3_ROOT}:")
    print('./ns3 run "AstraSimNetwork ' + " ".join(args) + '"')
    print(f"FCT output: {NS3_ROOT / manifest['fct_output']}")
    print("Annotate text outputs after the run:")
    print(manifest["annotation_command"])


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate physical topology and point-to-point Chakra workloads "
            "without changing the ASTRA-sim execution path."
        )
    )
    parser.add_argument("--scenario", required=True, help="Scenario JSON path")
    parser.add_argument(
        "--output-dir",
        default="examples/custom_network/generated",
        help="Generated input directory, relative to the repository root",
    )
    parser.add_argument(
        "--base-network-config",
        default="extern/network_backend/ns-3/scratch/config/config_clos.txt",
        help="Base ns-3 network configuration to rewrite",
    )
    args = parser.parse_args()

    scenario_path = resolve_repo_path(args.scenario)
    output_dir = resolve_repo_path(args.output_dir)
    base_network_config = resolve_repo_path(args.base_network_config)

    if not scenario_path.is_file():
        raise SystemExit(f"scenario does not exist: {scenario_path}")
    if not base_network_config.is_file():
        raise SystemExit(f"base network config does not exist: {base_network_config}")

    try:
        manifest = generate(scenario_path, output_dir, base_network_config)
    except (ScenarioError, json.JSONDecodeError) as error:
        raise SystemExit(f"invalid scenario: {error}") from error
    print_run_command(manifest)


if __name__ == "__main__":
    main()
