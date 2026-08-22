#!/bin/bash

set -e

cd extern/network_backend/ns-3
mkdir -p scratch/output/Vtopo-figure1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config1.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run1.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config2.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run2.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config3.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run3.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config4.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run4.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config5.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run5.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config6.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run6.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config7.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run7.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config8.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run8.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config9.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run9.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config10.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run10.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config11.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run11.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config12.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run12.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config13.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run13.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config14.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run14.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config15.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run15.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config16.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run16.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config17.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run17.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config18.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run18.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config19.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run19.log 2>&1

./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/Vtopo-figure1/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/Vtopo-figure1/network_config20.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/Vtopo-figure1/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/Vtopo-figure1/run20.log 2>&1
