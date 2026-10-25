#!/bin/bash
set -e

cd extern/network_backend/ns-3

mkdir -p scratch/output/packet_500kb_buffer
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/packet_500kb_buffer/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/packet_500kb_buffer/network_config.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/packet_500kb_buffer/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/packet_500kb_buffer/run.log 2>&1