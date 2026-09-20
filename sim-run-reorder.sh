#!/bin/bash
set -e

cd extern/network_backend/ns-3


mkdir -p scratch/output/flow_pathpinning_40percent_asym
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/flow_pathpinning/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/flow_pathpinning/network_config_40percent_asym.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/flow_pathpinning/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/flow_pathpinning_40percent_asym/run.log 2>&1