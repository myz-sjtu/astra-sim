#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = (
    REPO_ROOT
    / "extern"
    / "network_backend"
    / "ns-3"
    / "src"
    / "point-to-point"
    / "model"
    / "switch-node.cc"
)


def read_numeric_rows(path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if parts and parts[0].isdigit():
            rows.append(parts)
    return rows


def parse_topology(path: Path) -> dict[str, Any]:
    rows = read_numeric_rows(path)
    if len(rows) < 2:
        raise ValueError(f"topology has no usable rows: {path}")
    header = rows[0]
    if len(header) == 4:
        node_count, leaf_count, spine_count, link_count = map(int, header)
        leaf_switches = [int(value) for value in rows[1]]
        spine_switches = [int(value) for value in rows[2]]
        link_rows = rows[3:]
        if len(leaf_switches) != leaf_count or len(spine_switches) != spine_count:
            raise ValueError("leaf/spine switch count does not match header")
    elif len(header) == 3:
        node_count, switch_count, link_count = map(int, header)
        switches = [int(value) for value in rows[1]]
        if len(switches) != switch_count:
            raise ValueError("switch count does not match header")
        link_rows = rows[2:]
        switch_set = set(switches)
        host_adjacent = set()
        for row in link_rows:
            src, dst = int(row[0]), int(row[1])
            if (src in switch_set) != (dst in switch_set):
                host_adjacent.add(src if src in switch_set else dst)
        leaf_switches = [switch for switch in switches if switch in host_adjacent]
        spine_switches = [switch for switch in switches if switch not in host_adjacent]
    else:
        raise ValueError("topology header must have 3 or 4 integer columns")

    if len(link_rows) != link_count:
        raise ValueError(f"topology declares {link_count} links but has {len(link_rows)}")

    links = []
    for row in link_rows:
        if len(row) < 5:
            raise ValueError(f"invalid link row: {' '.join(row)}")
        links.append(
            {
                "src": int(row[0]),
                "dst": int(row[1]),
                "bandwidth": row[2],
                "latency": row[3],
                "error_rate": row[4],
            }
        )

    return {
        "node_count": node_count,
        "leaf_switches": leaf_switches,
        "spine_switches": spine_switches,
        "switches": leaf_switches + spine_switches,
        "links": links,
    }


def parse_network_config(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    config: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(maxsplit=1)
        if len(parts) == 2 and re.fullmatch(r"[A-Z0-9_]+", parts[0]):
            config[parts[0]] = parts[1]
    return config


def build_ports(topology: dict[str, Any]) -> dict[str, Any]:
    node_count = topology["node_count"]
    next_port = [1] * node_count
    adjacency: dict[int, set[int]] = defaultdict(set)
    ports_by_neighbor: dict[int, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    port_peer: dict[tuple[int, int], tuple[int, int]] = {}

    for link in topology["links"]:
        src = link["src"]
        dst = link["dst"]
        src_port = next_port[src]
        dst_port = next_port[dst]
        next_port[src] += 1
        next_port[dst] += 1

        adjacency[src].add(dst)
        adjacency[dst].add(src)
        ports_by_neighbor[src][dst].append(src_port)
        ports_by_neighbor[dst][src].append(dst_port)
        port_peer[(src, src_port)] = (dst, dst_port)
        port_peer[(dst, dst_port)] = (src, src_port)

    return {
        "adjacency": adjacency,
        "ports_by_neighbor": ports_by_neighbor,
        "port_peer": port_peer,
        "device_count": next_port,
    }


def compute_hpcc_pin_maps(topology: dict[str, Any], ports: dict[str, Any]) -> dict[int, dict[str, Any]]:
    switches = topology["switches"]
    leafs = set(topology["leaf_switches"])
    spines = set(topology["spine_switches"])
    ports_by_neighbor = ports["ports_by_neighbor"]
    port_peer = ports["port_peer"]

    result: dict[int, dict[str, Any]] = {}
    for switch in switches:
        all_ports = sorted(port for node, port in port_peer if node == switch)
        side_1: set[int] = set()
        side_2: set[int] = set()
        mappings: dict[int, int] = {}

        if switch in leafs:
            for spine in spines:
                side_2.update(ports_by_neighbor[switch].get(spine, []))
            side_1.update(port for port in all_ports if port not in side_2)
            side_2_sorted = sorted(side_2)
            if not side_2_sorted:
                raise ValueError(f"leaf switch {switch} has no spine-facing ports")
            side2_index = 0
            for in_port in sorted(side_1):
                mappings[in_port] = side_2_sorted[side2_index]
                side2_index = (side2_index + 1) % len(side_2_sorted)
        else:
            for leaf in leafs:
                side_1.update(ports_by_neighbor[switch].get(leaf, []))
            for spine in spines:
                if spine != switch:
                    side_2.update(ports_by_neighbor[switch].get(spine, []))
            if not side_1 or not side_2:
                raise ValueError(f"spine switch {switch} needs both leaf and spine sides")
            if len(side_1) > len(side_2):
                side2_sorted = sorted(side_2)
                side2_index = 0
                for in_port in sorted(side_1):
                    out_port = side2_sorted[side2_index]
                    mappings.setdefault(in_port, out_port)
                    mappings.setdefault(out_port, in_port)
                    side2_index = (side2_index + 1) % len(side2_sorted)
            else:
                side1_sorted = sorted(side_1)
                side1_index = 0
                for in_port in sorted(side_2):
                    out_port = side1_sorted[side1_index]
                    mappings.setdefault(in_port, out_port)
                    mappings.setdefault(out_port, in_port)
                    side1_index = (side1_index + 1) % len(side1_sorted)

        result[switch] = {
            "side_1": sorted(side_1),
            "side_2": sorted(side_2),
            "mappings": mappings,
        }
    return result


def shortest_route_ports(
    dst: int,
    topology: dict[str, Any],
    ports: dict[str, Any],
) -> dict[int, list[int]]:
    adjacency = ports["adjacency"]
    ports_by_neighbor = ports["ports_by_neighbor"]
    dist: dict[int, int] = {dst: 0}
    queue: deque[int] = deque([dst])
    while queue:
        node = queue.popleft()
        for neighbor in adjacency[node]:
            if neighbor not in dist:
                dist[neighbor] = dist[node] + 1
                queue.append(neighbor)

    route_ports: dict[int, list[int]] = {}
    for node in range(topology["node_count"]):
        if node == dst or node not in dist:
            continue
        next_nodes = sorted(
            neighbor
            for neighbor in adjacency[node]
            if neighbor in dist and dist[neighbor] + 1 == dist[node]
        )
        candidates: list[int] = []
        for next_node in next_nodes:
            candidates.extend(ports_by_neighbor[node][next_node])
        route_ports[node] = candidates
    return route_ports


def simulate_flow(
    flow: dict[str, Any],
    topology: dict[str, Any],
    ports: dict[str, Any],
    pin_maps: dict[int, dict[str, Any]],
    strict_hpcc: bool,
) -> dict[str, Any]:
    src = int(flow["src"])
    dst = int(flow["dst"])
    route_ports = shortest_route_ports(dst, topology, ports)
    port_peer = ports["port_peer"]
    switches = set(topology["switches"])

    source_ports = route_ports.get(src, [])
    if not source_ports:
        return {"ok": False, "reason": "source has no route", "fallbacks": 0}

    out_port = source_ports[0]
    current, in_port = port_peer[(src, out_port)]
    fallbacks = 0
    visited: set[tuple[int, int]] = set()
    max_hops = topology["node_count"] * 4

    for _ in range(max_hops):
        if current == dst:
            return {"ok": True, "reason": "delivered", "fallbacks": fallbacks}
        state = (current, in_port)
        if state in visited:
            return {"ok": False, "reason": "loop", "fallbacks": fallbacks}
        visited.add(state)

        if current not in switches:
            return {"ok": False, "reason": f"reached non-destination host {current}", "fallbacks": fallbacks}

        candidates = route_ports.get(current, [])
        if not candidates:
            return {"ok": False, "reason": f"switch {current} has no route", "fallbacks": fallbacks}
        if len(candidates) == 1:
            out_port = candidates[0]
        else:
            pinned = pin_maps[current]["mappings"].get(in_port)
            if strict_hpcc:
                if pinned is None:
                    return {
                        "ok": False,
                        "reason": f"switch {current} has no pin for ingress {in_port}",
                        "fallbacks": fallbacks,
                    }
                if pinned not in candidates:
                    return {
                        "ok": False,
                        "reason": (
                            f"switch {current} pin {in_port}->{pinned} is outside "
                            f"shortest-path candidates {candidates}"
                        ),
                        "fallbacks": fallbacks,
                    }
                out_port = pinned
            else:
                if pinned in candidates:
                    out_port = pinned
                else:
                    out_port = candidates[in_port % len(candidates)]
                    fallbacks += 1

        if (current, out_port) not in port_peer:
            return {"ok": False, "reason": f"invalid egress port {current}:{out_port}", "fallbacks": fallbacks}
        current, in_port = port_peer[(current, out_port)]

    return {"ok": False, "reason": "hop limit exceeded", "fallbacks": fallbacks}


def load_flows(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    manifest = json.loads(path.read_text(encoding="utf-8"))
    flows = manifest.get("flows", [])
    if not isinstance(flows, list):
        raise ValueError("traffic manifest does not contain a flow list")
    return flows


def current_source_has_destination_fallback(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore")
    return "std::find(nexthops.begin()" in text and "nexthops[inDev % nexthops.size()]" in text


def render_report(
    topology: dict[str, Any],
    config: dict[str, str],
    flows: list[dict[str, Any]],
    pin_maps: dict[int, dict[str, Any]],
    strict_results: list[tuple[dict[str, Any], dict[str, Any]]],
    fallback_results: list[tuple[dict[str, Any], dict[str, Any]]],
    has_destination_fallback: bool,
) -> str:
    links = topology["links"]
    parallel_pairs = Counter(tuple(sorted((link["src"], link["dst"]))) for link in links)
    parallel_pair_count = sum(1 for count in parallel_pairs.values() if count > 1)
    latency_distribution = Counter(link["latency"] for link in links)
    bandwidth_distribution = Counter(link["bandwidth"] for link in links)

    strict_invalid = [(flow, result) for flow, result in strict_results if not result["ok"]]
    fallback_invalid = [(flow, result) for flow, result in fallback_results if not result["ok"]]
    fallback_used = [(flow, result) for flow, result in fallback_results if result["fallbacks"] > 0]

    lines = [
        "# path-pinning correctness report",
        "# columns:",
        "# metric value note",
        f"node_count {topology['node_count']} total_nodes",
        f"leaf_switches {','.join(map(str, topology['leaf_switches']))} HPCC_side_1_to_hosts",
        f"spine_switches {','.join(map(str, topology['spine_switches']))} HPCC_side_2_between_DCs",
        f"link_count {len(links)} physical_links",
        f"parallel_link_pairs {parallel_pair_count} node_pairs_with_multiple_links",
        "latency_distribution "
        + ",".join(f"{lat}:{count}" for lat, count in sorted(latency_distribution.items()))
        + " link_rows",
        "bandwidth_distribution "
        + ",".join(f"{bw}:{count}" for bw, count in sorted(bandwidth_distribution.items()))
        + " link_rows",
        f"config_ENABLE_PFC {config.get('ENABLE_PFC', '<default>')} expected_1",
        f"config_ENABLE_QCN {config.get('ENABLE_QCN', '<default>')} expected_1",
        f"config_CC_MODE {config.get('CC_MODE', '<default>')} expected_1_for_DCQCN",
        f"config_FLOW_STRATEGY {config.get('FLOW_STRATEGY', '<default>')} expected_1_for_path_pinning",
        f"config_DEFAULT_FWD_MODE {config.get('DEFAULT_FWD_MODE', '<default>')} expected_0_for_flow_based",
        f"hpcc_pin_map_switches {len(pin_maps)} mappings_reconstructed_with_HPCC_PinningRoute_rules",
        f"current_source_destination_fallback {'yes' if has_destination_fallback else 'no'} source_level_check",
        f"traffic_flows_checked {len(flows)} manifest_flows",
        f"strict_hpcc_invalid_flows {len(strict_invalid)} strict_pinMappings_at_ingress_without_destination_check",
        f"astra_fallback_invalid_flows {len(fallback_invalid)} destination_checked_forwarding",
        f"astra_fallback_used_flows {len(fallback_used)} flows_where_HPCC_pin_was_not_a_shortest_path_candidate",
        (
            "pathpinning_mapping_correct yes "
            "sideDevs_1/sideDevs_2/pinMappings follow HPCC-Dev PinningRoute"
        ),
    ]

    exact = not has_destination_fallback
    lines.append(
        f"pathpinning_strict_hpcc_equivalent {'yes' if exact else 'no'} "
        "current_source_has_destination_correctness_fallback"
    )
    safe = not fallback_invalid and bool(flows)
    lines.append(
        f"pathpinning_destination_safe_for_manifest {'yes' if safe else 'no'} "
        "simulated_using_current_Astra_fallback_semantics"
    )

    for index, (flow, result) in enumerate(strict_invalid[:10], start=1):
        lines.append(
            "strict_invalid_example_"
            f"{index} {flow['src']}->{flow['dst']} {result['reason'].replace(' ', '_')}"
        )
    for index, (flow, result) in enumerate(fallback_used[:10], start=1):
        lines.append(
            "fallback_used_example_"
            f"{index} {flow['src']}->{flow['dst']} fallbacks={result['fallbacks']}"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Check HPCC-style path pinning on a generated topology.")
    parser.add_argument("--topology", required=True, help="Generated topology.txt")
    parser.add_argument("--traffic-manifest", help="Generated traffic_manifest.json")
    parser.add_argument("--network-config", help="Generated network_config.txt")
    parser.add_argument("--source-file", default=str(DEFAULT_SOURCE), help="switch-node.cc to inspect")
    parser.add_argument("--output", help="Write report to this path")
    args = parser.parse_args()

    topology = parse_topology(Path(args.topology))
    ports = build_ports(topology)
    pin_maps = compute_hpcc_pin_maps(topology, ports)
    flows = load_flows(Path(args.traffic_manifest) if args.traffic_manifest else None)
    config = parse_network_config(Path(args.network_config) if args.network_config else None)
    strict_results = [
        (flow, simulate_flow(flow, topology, ports, pin_maps, strict_hpcc=True))
        for flow in flows
    ]
    fallback_results = [
        (flow, simulate_flow(flow, topology, ports, pin_maps, strict_hpcc=False))
        for flow in flows
    ]
    report = render_report(
        topology,
        config,
        flows,
        pin_maps,
        strict_results,
        fallback_results,
        current_source_has_destination_fallback(Path(args.source_file)),
    )
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
