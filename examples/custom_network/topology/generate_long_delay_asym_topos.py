#!/usr/bin/env python3

from __future__ import annotations

import argparse
import random
from pathlib import Path


DEFAULT_SOURCE = "clos_2dc_64_long_topo_mul.txt"
DEFAULT_SEED = 20260821


def parse_header(lines: list[str]) -> tuple[int, int]:
    """Return the first topology line index and declared link count."""
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if not all(part.isdigit() for part in parts):
            continue
        if len(parts) == 3:
            return index, int(parts[2])
        if len(parts) == 4:
            return index, int(parts[3])
        raise ValueError(f"unsupported topology header at line {index + 1}: {line}")
    raise ValueError("topology header not found")


def format_delay_us(delay_us: float) -> str:
    rendered = f"{delay_us:.6f}".rstrip("0").rstrip(".")
    return f"{rendered}us"


def build_group_coefficients(groups: int, seed: int) -> list[float]:
    if groups < 2:
        raise ValueError("groups must be >= 2")
    coeffs = [(index - (groups - 1) / 2) / (groups - 1) for index in range(groups)]
    rng = random.Random(seed)
    rng.shuffle(coeffs)
    return coeffs


def update_long_link_delays(
    lines: list[str],
    long_src: str,
    long_dst: str,
    groups: int,
    spread_percent: int,
    base_delay_us: float,
    profile_seed: int,
) -> tuple[list[str], list[tuple[int, str]]]:
    header_index, link_count = parse_header(lines)
    link_start = header_index + 3 if len(lines[header_index].split()) == 4 else header_index + 2
    link_end = link_start + link_count
    if link_end > len(lines):
        raise ValueError("declared link count exceeds available topology rows")

    long_link_offsets: list[int] = []
    for offset, line in enumerate(lines[link_start:link_end]):
        parts = line.split()
        if len(parts) != 5:
            raise ValueError(f"link row {link_start + offset + 1} must have five columns")
        if parts[0] == long_src and parts[1] == long_dst:
            long_link_offsets.append(offset)

    if not long_link_offsets:
        raise ValueError(f"no long links found for {long_src}->{long_dst}")
    if len(long_link_offsets) % groups != 0:
        raise ValueError(
            f"found {len(long_link_offsets)} long links, not divisible by groups={groups}"
        )

    spread = spread_percent / 100.0
    coeffs = build_group_coefficients(groups, profile_seed)
    updated = list(lines)
    assigned: list[tuple[int, str]] = []
    for index, offset in enumerate(long_link_offsets):
        group_index = index % groups
        delay_us = base_delay_us * (1.0 + spread * coeffs[group_index])
        parts = updated[link_start + offset].split()
        parts[3] = format_delay_us(delay_us)
        updated[link_start + offset] = " ".join(parts)
        assigned.append((index + 1, parts[3]))

    return updated, assigned


def generate(args: argparse.Namespace) -> None:
    source = args.source.resolve()
    output_dir = args.output_dir.resolve()
    lines = source.read_text(encoding="utf-8").splitlines()
    output_dir.mkdir(parents=True, exist_ok=True)

    for spread_percent in args.spreads:
        if spread_percent < 1 or spread_percent > 100:
            raise ValueError("spread percent must be in [1, 100]")
        updated, assigned = update_long_link_delays(
            lines=lines,
            long_src=str(args.long_src),
            long_dst=str(args.long_dst),
            groups=args.groups,
            spread_percent=spread_percent,
            base_delay_us=args.base_delay_us,
            profile_seed=args.profile_seed,
        )
        output = output_dir / f"{args.prefix}_{spread_percent:02d}pct.txt"
        metadata = [
            "",
            "# long-distance delay asymmetry profile",
            f"# source: {source.name}",
            f"# long_link: {args.long_src}->{args.long_dst}",
            f"# spread_definition: (max_delay - min_delay) / mean_delay = {spread_percent}%",
            f"# base_delay_us: {args.base_delay_us:g}",
            f"# groups: {args.groups}",
            f"# profile_seed: {args.profile_seed}",
            "# link_idx_to_delay: "
            + " ".join(f"{link_idx}:{delay}" for link_idx, delay in assigned),
        ]
        output.write_text("\n".join(updated + metadata) + "\n", encoding="utf-8")
        print(output)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Generate topology variants with deterministic long-link delay asymmetry."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=script_dir / DEFAULT_SOURCE,
        help="Input topology file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=script_dir,
        help="Directory for generated topology files.",
    )
    parser.add_argument(
        "--prefix",
        default="clos_2dc_64_long_topo_mul_asym",
        help="Generated topology filename prefix.",
    )
    parser.add_argument("--long-src", type=int, default=68, help="Long-link source node ID.")
    parser.add_argument("--long-dst", type=int, default=69, help="Long-link destination node ID.")
    parser.add_argument(
        "--groups",
        type=int,
        default=8,
        help="Number of delay classes. The original 16 links use the 8-class profile twice.",
    )
    parser.add_argument(
        "--base-delay-us",
        type=float,
        default=500.0,
        help="Mean long-link delay in microseconds.",
    )
    parser.add_argument(
        "--profile-seed",
        type=int,
        default=DEFAULT_SEED,
        help="Seed used only for deterministic delay-class ordering.",
    )
    parser.add_argument(
        "--spreads",
        type=int,
        nargs="+",
        default=list(range(1, 11)),
        help="Asymmetry spread percentages to generate.",
    )
    generate(parser.parse_args())


if __name__ == "__main__":
    main()
