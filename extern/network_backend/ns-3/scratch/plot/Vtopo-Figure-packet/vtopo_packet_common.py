#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")

import matplotlib as mpl
from matplotlib import pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import FuncFormatter, MaxNLocator


SCRIPT_DIR = Path(__file__).resolve().parent
SCRATCH_DIR = SCRIPT_DIR.parents[1]
NS3_ROOT = SCRIPT_DIR.parents[2]
REPO_ROOT = SCRIPT_DIR.parents[5]
GENERATED_ROOT = REPO_ROOT / "examples" / "custom_network" / "generated"
DEFAULT_OUTPUT_ROOT = SCRATCH_DIR / "output" / "Vtopo-Figure-packet"
MB = 1000.0 * 1000.0

mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42
mpl.rcParams["font.family"] = "serif"
mpl.rcParams["font.serif"] = ["Times New Roman", "DejaVu Serif"]
mpl.rcParams["mathtext.fontset"] = "stix"

FIGSIZE = (9, 5.5)
AXIS_LABEL_FONT = FontProperties(weight="bold", size=20)
Y_AXIS_LABEL_FONT = FontProperties(weight="bold", size=16)
X_TICK_FONT = FontProperties(weight="bold", size=16)
Y_TICK_FONT = FontProperties(weight="bold", size=14)
LEGEND_FONT = FontProperties(weight="bold", size=14)
REORDER_AXIS_LABEL = "Reordering Buffer Occupancy (MB)"
THROUGHPUT_AXIS_LABEL = "Avg. Throughput (Gbps)"
NO_REORDER_FLOOR_MB = 0.001

STRATEGY_ORDER = ("path-pinning", "random", "DLB", "SGLB")
STRATEGY_LABEL = {
    "path-pinning": "Path-Pinning",
    "random": "Random",
    "DLB": "DLB",
    "SGLB": "SGLB",
}
STRATEGY_COLOR = {
    "path-pinning": "#4D4D4D",
    "random": "#D55E00",
    "DLB": "#0072B2",
    "SGLB": "#009E73",
}
STRATEGY_MARKER = {
    "path-pinning": "o",
    "random": "s",
    "DLB": "^",
    "SGLB": "D",
}

LINKDOWN_X = (0, 1, 2, 4)
ASYM_DELAY_X = (0, 1, 10, 20, 40)

LINKDOWN_DIRS = {
    0: {
        "path-pinning": "flow-pathpinning",
        "random": "packet_random",
        "DLB": "packet_dlb",
        "SGLB": "packet_glb",
    },
    1: {
        "path-pinning": "flow_pathpinning_1linkfail",
        "random": "packet_random_1linkfail",
        "DLB": "packet_dlb_1linkfail",
        "SGLB": "packet_glb_1linkfail",
    },
    2: {
        "path-pinning": "flow_pathpinning_2linkfail",
        "random": "packet_random_2linkfail",
        "DLB": "packet_dlb_2linkfail",
        "SGLB": "packet_glb_2linkfail",
    },
    4: {
        "path-pinning": "flow_pathpinning_4linkfail",
        "random": "packet_random_4linkfail",
        "DLB": "packet_dlb_4linkfail",
        "SGLB": "packet_glb_4linkfail",
    },
}

ASYM_DELAY_DIRS = {
    0: {
        "path-pinning": "flow_pathpinning",
        "random": "packet_random",
        "DLB": "packet_dlb",
        "SGLB": "packet_glb",
    },
    1: {
        "path-pinning": "flow_pathpinning_1percent_asym",
        "random": "packet_random_1percent_asym",
        "DLB": "packet_dlb_1percent_asym",
        "SGLB": "packet_glb_1percent_asym",
    },
    10: {
        "path-pinning": "flow_pathpinning_10percent_asym",
        "random": "packet_random_10percent_asym",
        "DLB": "packet_dlb_10percent_asym",
        "SGLB": "packet_glb_10percent_asym",
    },
    20: {
        "path-pinning": "flow_pathpinning_20percent_asym",
        "random": "packet_random_20percent_asym",
        "DLB": "packet_dlb_20percent_asym",
        "SGLB": "packet_glb_20percent_asym",
    },
    40: {
        "path-pinning": "flow_pathpinning_40percent_asym",
        "random": "packet_random_40percent_asym",
        "DLB": "packet_dlb_40percent_asym",
        "SGLB": "packet_glb_40percent_asym",
    },
}

LINKDOWN_IDEAL_CONFIGS = {
    0: GENERATED_ROOT / "flow_pathpinning" / "network_config.txt",
    1: GENERATED_ROOT / "flow_pathpinning" / "network_config_1linkfail.txt",
    2: GENERATED_ROOT / "flow_pathpinning" / "network_config_2linkfail.txt",
    4: GENERATED_ROOT / "flow_pathpinning" / "network_config_4linkfail.txt",
}

ASYM_DELAY_IDEAL_CONFIGS = {
    0: GENERATED_ROOT / "flow_pathpinning" / "network_config.txt",
    1: GENERATED_ROOT / "flow_pathpinning" / "network_config_1percent_asym.txt",
    10: GENERATED_ROOT / "flow_pathpinning" / "network_config_10percent_asym.txt",
    20: GENERATED_ROOT / "flow_pathpinning" / "network_config_20percent_asym.txt",
    40: GENERATED_ROOT / "flow_pathpinning" / "network_config_40percent_asym.txt",
}


@dataclass(frozen=True)
class LinkDownEntry:
    time_us: int
    src: int
    dst: int
    link_idx: int


@dataclass(frozen=True)
class NetworkConfig:
    topology_file: Path
    flow_file: Path
    link_down: tuple[LinkDownEntry, ...]


@dataclass(frozen=True)
class Link:
    src: int
    dst: int
    bandwidth_gbps: float
    pair_index: int


@dataclass(frozen=True)
class Topology:
    leaves: tuple[int, ...]
    spines: tuple[int, ...]
    links: tuple[Link, ...]
    host_leaf: dict[int, int]
    host_rate_gbps: dict[int, float]


@dataclass(frozen=True)
class Flow:
    src: int
    dst: int


def clean_lines(path: Path) -> list[str]:
    lines: list[str] = []
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            stripped = line.split("#", 1)[0].strip()
            if stripped:
                lines.append(stripped)
    return lines


def data_rows(path: Path):
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.split("#", 1)[0].strip()
            if not stripped:
                continue
            yield line_number, stripped.split()


def parse_int(value: str, path: Path, line_number: int, field_name: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise ValueError(f"{path}:{line_number}: invalid {field_name}: {value!r}") from exc


def parse_float(value: str, path: Path, line_number: int, field_name: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{path}:{line_number}: invalid {field_name}: {value!r}") from exc


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot compute mean of an empty series")
    return sum(values) / len(values)


def resolve_input_path(raw: str, config_path: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    candidates = (NS3_ROOT / path, config_path.parent / path, REPO_ROOT / path)
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return (NS3_ROOT / path).resolve()


def read_network_config(path: Path) -> NetworkConfig:
    if not path.exists():
        raise FileNotFoundError(f"network config not found: {path}")

    topology_file: Path | None = None
    flow_file: Path | None = None
    link_down: list[LinkDownEntry] = []
    lines = clean_lines(path)
    i = 0
    while i < len(lines):
        tokens = lines[i].split()
        key = tokens[0]
        if key == "TOPOLOGY_FILE" and len(tokens) >= 2:
            topology_file = resolve_input_path(tokens[1], path)
        elif key == "FLOW_FILE" and len(tokens) >= 2:
            flow_file = resolve_input_path(tokens[1], path)
        elif key == "LINK_DOWN":
            rest = tokens[1:]
            if len(rest) == 3:
                time_us = int(rest[0], 0)
                if time_us > 0:
                    link_down.append(LinkDownEntry(time_us, int(rest[1], 0), int(rest[2], 0), 0))
            elif len(rest) == 4:
                link_down.append(
                    LinkDownEntry(int(rest[0], 0), int(rest[1], 0), int(rest[2], 0), int(rest[3], 0))
                )
            else:
                if len(rest) == 1:
                    count = int(rest[0], 0)
                elif not rest:
                    i += 1
                    if i >= len(lines):
                        raise ValueError(f"{path}: LINK_DOWN count missing")
                    count = int(lines[i].split()[0], 0)
                else:
                    raise ValueError(f"{path}: invalid LINK_DOWN line: {lines[i]!r}")
                for _ in range(count):
                    i += 1
                    if i >= len(lines):
                        raise ValueError(f"{path}: LINK_DOWN entry missing")
                    parts = lines[i].split()
                    if len(parts) < 4:
                        raise ValueError(f"{path}: invalid LINK_DOWN entry: {lines[i]!r}")
                    link_down.append(
                        LinkDownEntry(int(parts[0], 0), int(parts[1], 0), int(parts[2], 0), int(parts[3], 0))
                    )
        i += 1

    if topology_file is None:
        raise ValueError(f"{path}: TOPOLOGY_FILE not found")
    if flow_file is None:
        raise ValueError(f"{path}: FLOW_FILE not found")
    if not topology_file.exists():
        raise FileNotFoundError(f"topology file not found: {topology_file}")
    if not flow_file.exists():
        raise FileNotFoundError(f"flow file not found: {flow_file}")
    return NetworkConfig(topology_file, flow_file, tuple(link_down))


def parse_rate_gbps(value: str) -> float:
    token = value.strip().lower()
    units = (
        ("gbps", 1.0),
        ("gbit/s", 1.0),
        ("mbps", 1e-3),
        ("mbit/s", 1e-3),
        ("kbps", 1e-6),
        ("kbit/s", 1e-6),
        ("bps", 1e-9),
        ("bit/s", 1e-9),
    )
    for suffix, multiplier in units:
        if token.endswith(suffix):
            return float(token[: -len(suffix)]) * multiplier
    return float(token) * 1e-9


def read_topology(path: Path) -> Topology:
    lines = clean_lines(path)
    if len(lines) < 3:
        raise ValueError(f"{path}: topology must contain header, leaves, and spines")

    header = lines[0].split()
    if len(header) < 4:
        raise ValueError(f"{path}: invalid topology header")
    link_count = int(header[3], 0)
    leaves = tuple(int(value, 0) for value in lines[1].split())
    spines = tuple(int(value, 0) for value in lines[2].split())
    switches = set(leaves) | set(spines)

    pair_counts: dict[tuple[int, int], int] = defaultdict(int)
    links: list[Link] = []
    host_leaf: dict[int, int] = {}
    host_rate_gbps: dict[int, float] = {}

    for offset, line in enumerate(lines[3 : 3 + link_count], start=4):
        parts = line.split()
        if len(parts) < 3:
            raise ValueError(f"{path}:{offset}: invalid topology link row")
        src = int(parts[0], 0)
        dst = int(parts[1], 0)
        bandwidth_gbps = parse_rate_gbps(parts[2])
        pair_key = tuple(sorted((src, dst)))
        pair_counts[pair_key] += 1
        links.append(Link(src, dst, bandwidth_gbps, pair_counts[pair_key]))

        if src in leaves and dst not in switches:
            host_leaf[dst] = src
            host_rate_gbps[dst] = bandwidth_gbps
        elif dst in leaves and src not in switches:
            host_leaf[src] = dst
            host_rate_gbps[src] = bandwidth_gbps

    if len(links) != link_count:
        raise ValueError(f"{path}: expected {link_count} links, parsed {len(links)}")
    return Topology(leaves, spines, tuple(links), host_leaf, host_rate_gbps)


def read_flows(path: Path) -> list[Flow]:
    rows = list(data_rows(path))
    if not rows:
        raise ValueError(f"{path}: no flow rows found")
    flow_count = int(rows[0][1][0], 0)
    flows: list[Flow] = []
    for line_number, parts in rows[1:]:
        if len(parts) < 2:
            raise ValueError(f"{path}:{line_number}: invalid flow row")
        flows.append(Flow(int(parts[0], 0), int(parts[1], 0)))
    if flow_count != len(flows):
        raise ValueError(f"{path}: header declares {flow_count} flows, parsed {len(flows)}")
    return flows


def active_leaf_spine_capacity_gbps(topology: Topology, link_down: tuple[LinkDownEntry, ...], leaf: int) -> float:
    down_all_pairs = set()
    down_specific = set()
    for entry in link_down:
        pair = tuple(sorted((entry.src, entry.dst)))
        if entry.link_idx == 0:
            down_all_pairs.add(pair)
        else:
            down_specific.add((pair, entry.link_idx))

    total = 0.0
    spines = set(topology.spines)
    for link in topology.links:
        pair = tuple(sorted((link.src, link.dst)))
        if pair in down_all_pairs or (pair, link.pair_index) in down_specific:
            continue
        if link.src == leaf and link.dst in spines:
            total += link.bandwidth_gbps
        elif link.dst == leaf and link.src in spines:
            total += link.bandwidth_gbps
    return total


def ideal_average_throughput_gbps(config_path: Path) -> float:
    config = read_network_config(config_path)
    topology = read_topology(config.topology_file)
    flows = read_flows(config.flow_file)
    flows_by_dst_leaf: dict[int, list[Flow]] = defaultdict(list)
    for flow in flows:
        if flow.dst not in topology.host_leaf:
            raise ValueError(f"{config.flow_file}: destination host {flow.dst} is not attached to a leaf")
        flows_by_dst_leaf[topology.host_leaf[flow.dst]].append(flow)

    ideal_values: list[float] = []
    for dst_leaf, leaf_flows in flows_by_dst_leaf.items():
        active_capacity = active_leaf_spine_capacity_gbps(topology, config.link_down, dst_leaf)
        fair_share = active_capacity / len(leaf_flows) if leaf_flows else 0.0
        for flow in leaf_flows:
            if flow.src not in topology.host_rate_gbps:
                raise ValueError(f"{config.flow_file}: source host {flow.src} has no NIC rate")
            if flow.dst not in topology.host_rate_gbps:
                raise ValueError(f"{config.flow_file}: destination host {flow.dst} has no NIC rate")
            ideal_values.append(min(topology.host_rate_gbps[flow.src], topology.host_rate_gbps[flow.dst], fair_share))
    return mean(ideal_values)


def read_reorder_mb(result_dir: Path) -> float:
    path = result_dir / "reorder_stats.txt"
    if not path.exists():
        raise FileNotFoundError(f"reorder stats not found: {path}")
    values: list[float] = []
    for line_number, parts in data_rows(path):
        if not parts[0][0].isdigit():
            continue
        if len(parts) <= 20:
            raise ValueError(f"{path}:{line_number}: expected peak_ooo_buffer_bytes column")
        values.append(parse_float(parts[20], path, line_number, "peak_ooo_buffer_bytes") / MB)
    if not values:
        raise ValueError(f"{path}: no reorder records found")
    return mean(values)


def read_average_throughput_gbps(result_dir: Path) -> float:
    path = result_dir / "fct.txt"
    if not path.exists():
        raise FileNotFoundError(f"FCT file not found: {path}")
    values: list[float] = []
    for line_number, parts in data_rows(path):
        if not parts[0][0].isdigit():
            continue
        if len(parts) < 11:
            raise ValueError(f"{path}:{line_number}: expected throughput_gbps column")
        values.append(parse_float(parts[10], path, line_number, "throughput_gbps"))
    if not values:
        raise ValueError(f"{path}: no FCT records found")
    return mean(values)


def build_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Vtopo packet output root. Default: {DEFAULT_OUTPUT_ROOT}",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=SCRIPT_DIR,
        help=f"Directory for generated PDF. Default: {SCRIPT_DIR}",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Do not print CSV-style values to stdout.",
    )
    return parser


def compact_float(value: float) -> str:
    if abs(value) >= 100:
        return f"{value:.0f}"
    if abs(value) >= 10:
        return f"{value:.1f}".rstrip("0").rstrip(".")
    if abs(value) >= 1:
        return f"{value:.2f}".rstrip("0").rstrip(".")
    if value == 0:
        return "0"
    return f"{value:.3f}".rstrip("0").rstrip(".")


def reorder_display_value(value: float) -> float:
    return NO_REORDER_FLOOR_MB if value <= 0 else value


def format_reorder_tick(value: float, _pos) -> str:
    if value <= NO_REORDER_FLOOR_MB * 1.01:
        return "0"
    return compact_float(value)


def style_axes(ax):
    ax.grid(True, linestyle="--", alpha=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", labelsize=16)
    ax.tick_params(axis="y", labelsize=14)
    for label in ax.get_xticklabels():
        label.set_fontproperties(X_TICK_FONT)
    for label in ax.get_yticklabels():
        label.set_fontproperties(Y_TICK_FONT)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("black")
        spine.set_linewidth(1.0)


def even_x_positions(x_values) -> list[int]:
    return list(range(len(x_values)))


def apply_even_x_axis(ax, x_values) -> None:
    ax.set_xticks(even_x_positions(x_values))
    ax.set_xticklabels([compact_float(float(value)) for value in x_values])


def apply_reorder_scale(ax, values: list[float], has_zero: bool, force_log: bool = False) -> None:
    max_value = max(values) if values else 0.0
    positives = [value for value in values if value > 0]
    use_log = force_log
    if positives:
        min_positive = min(positives)
        use_log = use_log or has_zero or max_value / min_positive >= 100.0
    if use_log:
        bottom = NO_REORDER_FLOOR_MB * 0.7
        top = max(max_value * 1.3, NO_REORDER_FLOOR_MB * 10)
        ticks = [NO_REORDER_FLOOR_MB]
        for tick in (0.01, 0.1, 1.0, 5.0, 10.0, 50.0, 100.0):
            if bottom < tick < top:
                ticks.append(tick)
        ax.set_yscale("log")
        ax.set_ylim(bottom=bottom, top=top)
        ax.set_yticks(ticks)
        ax.yaxis.set_major_formatter(FuncFormatter(format_reorder_tick))
    else:
        min_value = min(values) if values else 0.0
        span = max(max_value - min_value, max_value * 0.2, 0.01)
        ax.set_ylim(bottom=max(0.0, min_value - span * 0.2), top=max_value + span * 0.2)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: compact_float(value)))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6))


def apply_throughput_scale(ax, values: list[float]) -> None:
    max_value = max(values) if values else 0.0
    ax.set_ylim(bottom=0.0, top=max(max_value * 1.14, 10.0))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: compact_float(value)))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))


def apply_distance_scale(ax, values: list[float]) -> None:
    max_value = max(values) if values else 0.0
    top = max(max_value * 1.12, 0.1)
    bottom = -top * 0.08
    ticks = [tick for tick in MaxNLocator(nbins=6).tick_values(0.0, top) if 0 <= tick <= top]
    if 0.0 not in ticks:
        ticks.insert(0, 0.0)
    ax.set_ylim(bottom=bottom, top=top)
    ax.set_yticks(ticks)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: compact_float(value)))


def print_summary(title: str, x_label: str, y_label: str, x_values, series, ideal=None) -> None:
    print(title)
    print(f"{x_label},strategy,{y_label}")
    for x_value in x_values:
        for strategy in STRATEGY_ORDER:
            print(f"{x_value},{strategy},{series[strategy][x_values.index(x_value)]:.6f}")
        if ideal is not None:
            print(f"{x_value},Ideal Throughput,{ideal[x_values.index(x_value)]:.6f}")


def collect_series(output_root: Path, experiment: str, metric: str) -> tuple[list[int], dict[str, list[float]]]:
    if experiment == "linkdown":
        group = output_root / "multi-linkdown"
        x_values = list(LINKDOWN_X)
        dir_map = LINKDOWN_DIRS
    elif experiment == "asym-delay":
        group = output_root / "asym-delay"
        x_values = list(ASYM_DELAY_X)
        dir_map = ASYM_DELAY_DIRS
    else:
        raise ValueError(f"unknown experiment: {experiment}")

    reader = read_reorder_mb if metric == "reorder" else read_average_throughput_gbps
    series: dict[str, list[float]] = {strategy: [] for strategy in STRATEGY_ORDER}
    for x_value in x_values:
        for strategy in STRATEGY_ORDER:
            result_dir = group / dir_map[x_value][strategy]
            if not result_dir.exists():
                raise FileNotFoundError(f"result directory not found: {result_dir}")
            series[strategy].append(reader(result_dir))
    return x_values, series


def collect_ideal_series(experiment: str) -> list[float]:
    configs = LINKDOWN_IDEAL_CONFIGS if experiment == "linkdown" else ASYM_DELAY_IDEAL_CONFIGS
    x_values = LINKDOWN_X if experiment == "linkdown" else ASYM_DELAY_X
    return [ideal_average_throughput_gbps(configs[x_value]) for x_value in x_values]


def draw_plot(
    x_values: list[int],
    series: dict[str, list[float]],
    x_label: str,
    y_label: str,
    output_path: Path,
    ideal: list[float] | None = None,
    yscale: str = "auto",
) -> None:
    if yscale not in {"auto", "linear", "log"}:
        raise ValueError(f"unsupported yscale: {yscale}")

    fig, ax = plt.subplots(figsize=FIGSIZE)
    x_positions = even_x_positions(x_values)
    all_values: list[float] = []
    has_zero = False
    for strategy in STRATEGY_ORDER:
        raw_values = series[strategy]
        if ideal is not None or yscale == "linear":
            values = raw_values
        else:
            values = [reorder_display_value(value) for value in raw_values]
        has_zero = has_zero or any(value <= 0 for value in raw_values)
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

    if ideal is not None:
        all_values.extend(ideal)
        ax.plot(
            x_positions,
            ideal,
            label="Ideal",
            color="black",
            linestyle="--",
            marker="x",
            markersize=7,
            linewidth=2.0,
        )

    ax.set_xlabel(x_label, fontproperties=AXIS_LABEL_FONT)
    ax.set_ylabel(y_label, fontproperties=Y_AXIS_LABEL_FONT)
    apply_even_x_axis(ax, x_values)
    ax.margins(x=0.08)
    if ideal is None:
        if yscale == "linear":
            apply_distance_scale(ax, all_values)
        else:
            apply_reorder_scale(ax, all_values, has_zero, force_log=yscale == "log")
    else:
        apply_throughput_scale(ax, all_values)
    style_axes(ax)
    ax.legend(
        prop=LEGEND_FONT,
        ncol=5 if ideal is not None else 4,
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


def run_reorder_plot(experiment: str, output_name: str, x_label: str, default_yscale: str = "auto") -> None:
    parser = build_parser(f"Plot {experiment} reorder severity for Vtopo packet results.")
    parser.add_argument(
        "--yscale",
        choices=("auto", "linear", "log"),
        default=default_yscale,
        help=f"Y-axis scale for reorder severity. Default: {default_yscale}.",
    )
    args = parser.parse_args()
    x_values, series = collect_series(args.output_root, experiment, "reorder")
    suffix = "_logy" if args.yscale == "log" else ""
    output_path = args.out_dir / f"{output_name}{suffix}.pdf"
    draw_plot(x_values, series, x_label, REORDER_AXIS_LABEL, output_path, yscale=args.yscale)
    if not args.no_summary:
        print_summary(output_name, x_label, REORDER_AXIS_LABEL, x_values, series)
    print(f"Saved {output_path}")


def draw_distance_plot(
    x_values: list[int],
    series: dict[str, list[float]],
    x_label: str,
    y_label: str,
    output_path: Path,
    yscale: str = "linear",
) -> None:
    if yscale not in {"linear", "log"}:
        raise ValueError(f"unsupported distance yscale: {yscale}")

    fig, ax = plt.subplots(figsize=FIGSIZE)
    x_positions = even_x_positions(x_values)
    all_values: list[float] = []
    has_zero = False
    for strategy in STRATEGY_ORDER:
        raw_values = series[strategy]
        has_zero = has_zero or any(value <= 0 for value in raw_values)
        values = raw_values if yscale == "linear" else [reorder_display_value(value) for value in raw_values]
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

    ax.set_xlabel(x_label, fontproperties=AXIS_LABEL_FONT)
    ax.set_ylabel(y_label, fontproperties=Y_AXIS_LABEL_FONT)
    apply_even_x_axis(ax, x_values)
    ax.margins(x=0.08)
    if yscale == "linear":
        apply_distance_scale(ax, all_values)
    else:
        apply_reorder_scale(ax, all_values, has_zero)
    style_axes(ax)
    ax.legend(
        prop=LEGEND_FONT,
        ncol=4,
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


def run_throughput_plot(experiment: str, output_name: str, x_label: str) -> None:
    parser = build_parser(f"Plot {experiment} average throughput for Vtopo packet results.")
    args = parser.parse_args()
    x_values, series = collect_series(args.output_root, experiment, "throughput")
    ideal = collect_ideal_series(experiment)
    output_path = args.out_dir / f"{output_name}.pdf"
    draw_plot(x_values, series, x_label, THROUGHPUT_AXIS_LABEL, output_path, ideal=ideal)
    if not args.no_summary:
        print_summary(output_name, x_label, THROUGHPUT_AXIS_LABEL, x_values, series, ideal)
    print(f"Saved {output_path}")
