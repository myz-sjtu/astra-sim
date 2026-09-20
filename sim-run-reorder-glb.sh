#!/bin/bash
set -e

cd extern/network_backend/ns-3

mkdir -p scratch/output/packet_glb
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/packet_glb/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/packet_glb/network_config.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/packet_glb/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/packet_glb/run.log 2>&1

mkdir -p scratch/output/packet_glb_1linkfail
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/packet_glb/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/packet_glb/network_config_1linkfail.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/packet_glb/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/packet_glb_1linkfail/run.log 2>&1


mkdir -p scratch/output/packet_glb_2linkfail
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/packet_glb/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/packet_glb/network_config_2linkfail.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/packet_glb/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/packet_glb_2linkfail/run.log 2>&1

mkdir -p scratch/output/packet_glb_4linkfail
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/packet_glb/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/packet_glb/network_config_4linkfail.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/packet_glb/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/packet_glb_4linkfail/run.log 2>&1

mkdir -p scratch/output/packet_glb_1percent_asym
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/packet_glb/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/packet_glb/network_config_1percent_asym.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/packet_glb/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/packet_glb_1percent_asym/run.log 2>&1

mkdir -p scratch/output/packet_glb_5percent_asym
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/packet_glb/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/packet_glb/network_config_5percent_asym.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/packet_glb/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/packet_glb_5percent_asym/run.log 2>&1

mkdir -p scratch/output/packet_glb_10percent_asym
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/packet_glb/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/packet_glb/network_config_10percent_asym.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/packet_glb/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/packet_glb_10percent_asym/run.log 2>&1

mkdir -p scratch/output/packet_glb_20percent_asym
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/packet_glb/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/packet_glb/network_config_20percent_asym.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/packet_glb/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/packet_glb_20percent_asym/run.log 2>&1
