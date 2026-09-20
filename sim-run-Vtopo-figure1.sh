#!/bin/bash

set -e

cd extern/network_backend/ns-3
mkdir -p scratch/output/Vtopo-figure1-test

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/network_config5.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1-test/run5.log 2>&1


./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/network_config6.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1-test/run6.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/network_config7.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1-test/run7.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/network_config8.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1-test/run8.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/network_config9.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1-test/run9.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/network_config10.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1-test/run10.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/network_config11.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1-test/run11.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/network_config12.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1-test/run12.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/network_config13.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1-test/run13.log 2>&1


./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/network_config14.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1-test/run14.log 2>&1


./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/network_config15.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1-test/run15.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/network_config16.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1-test/run16.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/network_config17.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1-test/run17.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/network_config18.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1-test/run18.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/network_config19.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1-test/run19.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/network_config20.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1-test/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1-test/run20.log 2>&1