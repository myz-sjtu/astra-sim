#!/bin/bash
set -e

cd extern/network_backend/ns-3

mkdir -p scratch/output/flow_pathpinning
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/flow_pathpinning/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/flow_pathpinning/network_config.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/flow_pathpinning/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/flow_pathpinning/run.log 2>&1

mkdir -p scratch/output/flow_pathpinning_1linkfail
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/flow_pathpinning/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/flow_pathpinning/network_config_1linkfail.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/flow_pathpinning/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/flow_pathpinning_1linkfail/run.log 2>&1


mkdir -p scratch/output/flow_pathpinning_2linkfail
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/flow_pathpinning/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/flow_pathpinning/network_config_2linkfail.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/flow_pathpinning/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/flow_pathpinning_2linkfail/run.log 2>&1

mkdir -p scratch/output/flow_pathpinning_4linkfail
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/flow_pathpinning/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/flow_pathpinning/network_config_4linkfail.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/flow_pathpinning/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/flow_pathpinning_4linkfail/run.log 2>&1

mkdir -p scratch/output/flow_pathpinning_1percent_asym
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/flow_pathpinning/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/flow_pathpinning/network_config_1percent_asym.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/flow_pathpinning/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/flow_pathpinning_1percent_asym/run.log 2>&1

mkdir -p scratch/output/flow_pathpinning_5percent_asym
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/flow_pathpinning/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/flow_pathpinning/network_config_5percent_asym.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/flow_pathpinning/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/flow_pathpinning_5percent_asym/run.log 2>&1

mkdir -p scratch/output/flow_pathpinning_10percent_asym
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/flow_pathpinning/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/flow_pathpinning/network_config_10percent_asym.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/flow_pathpinning/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/flow_pathpinning_10percent_asym/run.log 2>&1

mkdir -p scratch/output/flow_pathpinning_20percent_asym
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/flow_pathpinning/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/flow_pathpinning/network_config_20percent_asym.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/flow_pathpinning/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/flow_pathpinning_20percent_asym/run.log 2>&1
