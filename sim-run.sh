#!/bin/bash
set -e  # 任何命令出错即退出

echo "=== 开始生成自定义网络输入 ==="
cd /root/astra-sim

python3 examples/custom_network/generate_custom_inputs.py \
  --scenario examples/custom_network/scenario_case2.json \
  --output-dir examples/custom_network/generated/case2 \
  --base-network-config examples/custom_network/config_case2.txt

echo "=== 进入 ns-3 目录并准备运行仿真 ==="
cd /root/astra-sim/extern/network_backend/ns-3

mkdir -p scratch/output/case2_arn_glb   # 确保重定向日志的目录存在

echo "=== 启动 AstraSimNetwork 仿真 ==="
./ns3 run "AstraSimNetwork \
  --workload-configuration=../../../examples/custom_network/generated/case2/workload/custom_traffic \
  --system-configuration=../../../examples/system/native_collectives/Ring_4chunks.json \
  --network-configuration=../../../examples/custom_network/generated/case2/network_config.txt \
  --remote-memory-configuration=../../../examples/remote_memory/analytical/no_memory_expansion.json \
  --logical-topology-configuration=../../../examples/custom_network/generated/case2/logical_topology.json \
  --comm-group-configuration=empty" > scratch/output/case2_arn_glb/run.log 2>&1

echo "=== 仿真完成，日志已保存至 scratch/output/case2_arn_glb/run.log ==="