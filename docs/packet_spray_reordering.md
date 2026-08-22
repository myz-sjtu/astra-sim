# 逐包 Packet-Spray 乱序统计

## 背景

ns-3 后端中，`fwd_mode=1` 或 `DEFAULT_FWD_MODE=1` 会让 RDMA data packet 使用 packet-spray 转发；`PACKET_STRATEGY=0` 表示交换机按 ingress port 对可用下一跳做 round-robin，`PACKET_STRATEGY=1` 表示对可用下一跳做逐包随机选择。逐包喷洒能提升多路径利用率，但同一 flow 的连续包会经过不同路径，不同路径上的传播时延、排队、PFC/ECN、链路故障和重路由会让高序号包先到达接收端。

接收端只能推进从 `ReceiverNextExpectedSeq` 开始的连续字节前缀。乱序包提前到达时会进入 OOO 缓存，ACK 只能确认连续前缀，因此发送窗口可能无法及时滑动；在更极端情况下，NACK/RTO/重传会进一步增加有效负载以外的网络负担。宏观表现通常是 FCT 增大、有效吞吐下降、尾延迟变差。

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

## 输出文件

`REORDER_OUTPUT_FILE` 指定输出路径；自定义网络生成脚本默认写为 `scratch/output/<scenario>/reorder_stats.txt`。旧配置未设置该项时，程序回退到 `fct.txt` 同目录下的 `reorder_stats.txt`。

输出列固定为：

```text
sip_hex dip_hex src_id dst_id tag sport dport pg fwd_mode total_data_packets total_payload_bytes ooo_packet_count ooo_ratio late_packet_count late_ratio duplicate_packet_count avg_reorder_distance_packets max_reorder_distance_packets max_reorder_distance_bytes peak_ooo_buffer_packets peak_ooo_buffer_bytes ooo_wait_events avg_ooo_wait_ns max_ooo_wait_ns
```

`fwd_mode=1` 的行是 packet-spray 主体；`fwd_mode=0` 行可作为 flow-based 对照或用于检查场景是否真正开启逐包转发。
