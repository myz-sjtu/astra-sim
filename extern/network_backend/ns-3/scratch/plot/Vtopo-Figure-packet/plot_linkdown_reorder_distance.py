#!/usr/bin/env python3

from pathlib import Path

from vtopo_packet_common import (
    LINKDOWN_DIRS,
    LINKDOWN_X,
    MIB,
    STRATEGY_ORDER,
    build_parser,
    data_rows,
    draw_distance_plot,
    mean,
    parse_float,
    print_summary,
)


Y_LABEL = "Max Reorder Distance (MiB)"


def read_reorder_extent_mib(result_dir: Path) -> float:
    path = result_dir / "reorder_stats.txt"
    if not path.exists():
        raise FileNotFoundError(f"reorder stats not found: {path}")

    values: list[float] = []
    for line_number, parts in data_rows(path):
        if not parts[0][0].isdigit():
            continue
        if len(parts) <= 18:
            raise ValueError(f"{path}:{line_number}: expected max_reorder_distance_bytes column")
        values.append(parse_float(parts[18], path, line_number, "max_reorder_distance_bytes") / MIB)
    if not values:
        raise ValueError(f"{path}: no reorder records found")
    return mean(values)


def main() -> None:
    parser = build_parser("Plot link-failure reorder extent for Vtopo packet results.")
    parser.add_argument(
        "--yscale",
        choices=("linear", "log"),
        default="linear",
        help="Y-axis scale for max reorder distance. Default: linear.",
    )
    args = parser.parse_args()

    x_values = list(LINKDOWN_X)
    series: dict[str, list[float]] = {strategy: [] for strategy in STRATEGY_ORDER}
    for failed_links in x_values:
        for strategy in STRATEGY_ORDER:
            result_dir = args.output_root / "multi-linkdown" / LINKDOWN_DIRS[failed_links][strategy]
            series[strategy].append(read_reorder_extent_mib(result_dir))

    suffix = "_logy" if args.yscale == "log" else ""
    output_path = args.out_dir / f"vtopo_packet_linkdown_reorder_distance{suffix}.pdf"
    draw_distance_plot(x_values, series, "Failed Links", Y_LABEL, output_path, yscale=args.yscale)
    if not args.no_summary:
        print_summary("vtopo_packet_linkdown_reorder_distance", "Failed Links", Y_LABEL, x_values, series)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
