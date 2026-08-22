#!/bin/bash
set -e

python3 examples/custom_network/generate_custom_inputs.py \
--scenario examples/custom_network/scenario_2dc_64_hd_allreduce.json \
--output-dir examples/custom_network/generated/hd_path_pinning_linkfail_shallowbuffer

cd extern/network_backend/ns-3
mkdir -p scratch/output/hd_path_pinning_linkfail_shallowbuffer

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/hd_path_pinning_linkfail_shallowbuffer/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/hd_path_pinning_linkfail_shallowbuffer/network_config.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/hd_path_pinning_linkfail_shallowbuffer/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/hd_path_pinning_linkfail_shallowbuffer/run.log 2>&1