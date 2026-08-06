#!/bin/bash
set -e

python3 examples/custom_network/generate_custom_inputs.py \
--scenario examples/custom_network/scenario_2dc_64_clos.json \
--output-dir examples/custom_network/generated/2dc_64_clos

cd extern/network_backend/ns-3
mkdir -p scratch/output/2dc_64_clos

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/2dc_64_clos/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/2dc_64_clos/network_config11.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/2dc_64_clos/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/2dc_64_clos/run11.log 2>&1