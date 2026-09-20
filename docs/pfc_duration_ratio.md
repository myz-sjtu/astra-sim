# PFC Duration Ratio

This note defines an offline statistic for ASTRA-sim ns-3 runs that emit
`fct.txt` and `pfc.txt`.

## Input files

- `fct.txt`: one completed flow per row. The relevant columns are
  `start_time_ns` and `fct_ns`; flow finish time is
  `start_time_ns + fct_ns`.
- `pfc.txt`: one PFC event per row with columns
  `time_ns node_id node_type if_index type`; `type=1` is pause and `type=0`
  is resume.

## Main metric

The active flow window is:

```text
window_start_ns = min(flow.start_time_ns)
window_end_ns   = max(flow.start_time_ns + flow.fct_ns)
window_ns       = window_end_ns - window_start_ns
```

For each receiving device port `(node_id, node_type, if_index)`, pair pause and
resume events to form half-open intervals `[pause_time, resume_time)`. Clip each
interval to the active flow window, then sum durations across all ports:

```text
total_pause_ns = sum(clipped pause interval duration across all ports)
pfc_duration_ratio = total_pause_ns / window_ns
```

This formula is reasonable as a congestion-pressure metric, but it is not a pure
percentage. Because the numerator sums port-time, concurrent pauses on multiple
ports add up, so `pfc_duration_ratio` can be greater than `1.0`. Interpreted
literally, it is the average number of paused ports over the active flow window.

## Normalized variants

Use a normalized ratio when the desired output is a percentage:

```text
observed_port_pause_fraction = total_pause_ns / (observed_paused_ports * window_ns)
network_port_pause_fraction  = total_pause_ns / (total_directional_ports * window_ns)
```

- `observed_port_pause_fraction` answers: among ports that ever paused, what
  fraction of the active window were they paused on average?
- `network_port_pause_fraction` answers: across all QBB directional ports, what
  fraction of port-time was paused? Provide `--port-count` or `--topology` to
  compute this.

## Edge handling

- Duplicate pause before resume is treated as a repeated pause signal, not a new
  overlapping pause interval.
- Resume without a prior pause is counted and ignored for duration.
- Pause without a later resume is closed at `window_end_ns` by default; use
  `--open-interval-policy drop` to exclude it instead. The script reports both
  closed and dropped open intervals.
- If FCT contains only completed flows, unfinished flows are not represented in
  the default window. Use explicit `--window-start-ns` and `--window-end-ns` when
  analyzing incomplete runs or disjoint workload phases.

## Usage

```bash
python3 examples/custom_network/analyze_pfc_duration.py \
  --output-dir extern/network_backend/ns-3/scratch/output/<scenario> \
  --topology examples/custom_network/generated/<scenario>/topology.txt \
  --summary-csv pfc_duration_summary.csv \
  --per-port-csv pfc_duration_ports.csv
```

For numbered run outputs, pass explicit files:

```bash
python3 examples/custom_network/analyze_pfc_duration.py \
  --fct extern/network_backend/ns-3/scratch/output/2dc_64_clos/fct1.txt \
  --pfc extern/network_backend/ns-3/scratch/output/2dc_64_clos/pfc1.txt \
  --format json
```
