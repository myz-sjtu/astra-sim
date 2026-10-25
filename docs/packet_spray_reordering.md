# 逐包 Packet-Spray 乱序统计

## 背景

ns-3 后端中，`fwd_mode=1` 或 `DEFAULT_FWD_MODE=1` 会让 RDMA data packet 使用 packet-spray 转发；`PACKET_STRATEGY=0` 表示交换机按 ingress port 对可用下一跳做 flow-base round-robin，`PACKET_STRATEGY=1` 表示对可用下一跳做逐包随机选择，`PACKET_STRATEGY=2` 表示 DLB：按目标 priority group 的 egress queue bytes 选择排队最少的一半下一跳，再从中随机选一个端口。逐包喷洒能提升多路径利用率，但同一 flow 的连续包会经过不同路径，不同路径上的传播时延、排队、PFC/ECN、链路故障和重路由会让高序号包先到达接收端。

接收端只能推进从 `ReceiverNextExpectedSeq` 开始的连续字节前缀。乱序包提前到达时会进入 OOO 缓存，ACK 只能确认连续前缀，因此发送窗口可能无法及时滑动；在更极端情况下，NACK/RTO/重传会进一步增加有效负载以外的网络负担。宏观表现通常是 FCT 增大、有效吞吐下降、尾延迟变差。

## Flow-base RR 设计

原始 RR 只使用 `m_rrCounter[inDev] % nexthops.size()`，同步启动且包大小一致的 flow 容易在不同 ingress port 上保持相同初始相位。当前 `PACKET_STRATEGY=0` 直接在原 RR 实现上叠加 flow base：

```text
flow_base = hash(sip, dip, sport, dport, pg, inDev) % nexthops
idx       = (m_rrCounter[inDev] + flow_base) % nexthops
```

这样仍保留 ingress-port RR counter 和逐包轮询行为，但不同 flow 的起始相位由 flow key 打散，避免同步流的首包和后续周期性包集中落到同一下一跳端口。

## DLB 设计

`PACKET_STRATEGY=2` 读取每个可用下一跳在当前 `pg` 上的 `m_mmu->egress_bytes[outDev][pg]`，按队列字节数从小到大排序。为避免大量同步包都压到当前单一最短队列，DLB 不直接返回全局最小端口，而是在排序后的最优半数端口中随机选择；候选数为奇数时向上取整，保证至少有一个候选端口。

## 统计位置

统计点位于 `RdmaHw::ReceiverCheckSeq`，以接收端真实到达顺序为准，只统计 RDMA data packet，不统计 ACK、NACK、CNP、PFC 等控制包。序号使用 `ch.udp.seq`，该值是 flow 内的发送字节偏移；`ReceiverNextExpectedSeq` 表示接收端下一个期望收到的字节序号。

## 指标定义

- `total_data_packets`: 接收端收到的 RDMA data packet 数量。
- `total_payload_bytes`: 接收端收到的 RDMA data payload bytes，包含重复包。
- `ooo_packet_count`: 到达时 `seq > ReceiverNextExpectedSeq` 的包数，表示提前到达并制造接收端空洞。
- `ooo_ratio`: `ooo_packet_count / total_data_packets`。
- `late_packet_count`: 非重复包且 `seq < max_seen_seq_before` 的包数，表示该包晚于更高序号包到达。
- `late_ratio`: `late_packet_count / total_data_packets`。
- `duplicate_packet_count`: `seq < ReceiverNextExpectedSeq` 或已在 OOO 缓存中的重复 data packet 数量。
- `avg_reorder_distance_packets`: 对所有 `seq > ReceiverNextExpectedSeq` 的包，统计 `ceil((seq - ReceiverNextExpectedSeq) / PACKET_PAYLOAD_SIZE)` 的平均值。
- `max_reorder_distance_packets`: 上述 packet-distance 的最大值。
- `max_reorder_distance_bytes`: `seq - ReceiverNextExpectedSeq` 的最大字节距离。
- `peak_ooo_buffer_packets`: 接收端 OOO 缓存中同时存在的最大包数。
- `peak_ooo_buffer_bytes`: 接收端 OOO 缓存中同时存在的最大 payload bytes。
- `ooo_wait_events`: 提前缓存、随后因低序号包补齐而被连续前缀释放的包数。
- `avg_ooo_wait_ns`: OOO 包从提前到达到被释放的平均等待时间。
- `max_ooo_wait_ns`: OOO 包最大等待时间。
- `ooo_receive_mode`: `0` 为无限 OOO buffer，`1` 为有限 per-Rx-QP OOO buffer + NACK/GBN，`2` 为未来 SACK/选择性重传预留模式，目前不实现。
- `ooo_buffer_limit_bytes`: 当前 Rx QP 的 OOO payload buffer 上限；无限模式为 `0`。
- `ooo_overflow_packet_count` / `ooo_overflow_bytes`: 因有限 OOO buffer 无法缓存而被拒绝的乱序包数和字节数。
- `gbn_flush_packet_count` / `gbn_flush_bytes`: 有限 buffer 溢出实际触发 NACK/GBN 时，接收端主动丢弃的已缓存乱序包数和 payload 字节数。
- `gbn_recovery_drop_packet_count` / `gbn_recovery_drop_bytes`: GBN 恢复期间，在缺口包到达前被直接丢弃的后续乱序包数和 payload 字节数。
- `nack_count`: 该 Rx QP 实际发送的 NACK 数量，包括有限 OOO buffer 溢出触发的 NACK。
- `remaining_ooo_packets` / `remaining_ooo_bytes`: QP 完成统计时仍留在 OOO buffer 中的包数和 payload bytes。

## 输出文件

`REORDER_OUTPUT_FILE` 指定输出路径；自定义网络生成脚本默认写为 `scratch/output/<scenario>/reorder_stats.txt`。旧配置未设置该项时，程序回退到 `fct.txt` 同目录下的 `reorder_stats.txt`。

输出列固定为：

```text
sip_hex dip_hex src_id dst_id tag sport dport pg fwd_mode total_data_packets total_payload_bytes ooo_packet_count ooo_ratio late_packet_count late_ratio duplicate_packet_count avg_reorder_distance_packets max_reorder_distance_packets max_reorder_distance_bytes peak_ooo_buffer_packets peak_ooo_buffer_bytes ooo_wait_events avg_ooo_wait_ns max_ooo_wait_ns ooo_receive_mode ooo_buffer_limit_bytes ooo_overflow_packet_count ooo_overflow_bytes gbn_flush_packet_count gbn_flush_bytes gbn_recovery_drop_packet_count gbn_recovery_drop_bytes nack_count remaining_ooo_packets remaining_ooo_bytes
```

`fwd_mode=1` 的行是 packet-spray 主体；`fwd_mode=0` 行可作为 flow-based 对照或用于检查场景是否真正开启逐包转发。

长时间批量仿真建议保持 `VERBOSE_OUTPUT=0`。该选项关闭 RDMA 速率控制、接收异常、NIC pause、MMU headroom 和 ARN trace 的高频 stdout 调试输出，不影响 `fct.txt`、`reorder_stats.txt`、`pfc.txt` 和 drop 统计文件；需要定位这些问题时设置为 `1`，并在需要时同时设置 `ENABLE_ARN_TRACE=1`。
