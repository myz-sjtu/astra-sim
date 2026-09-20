#ifndef ARN_HEADER_H
#define ARN_HEADER_H

#include "ns3/header.h"
#include "ns3/nstime.h"
#include "ns3/simulator.h"
#include <cstdint>
#include <functional>

namespace ns3 {

class ArnHeader : public Header {
public:
  struct FlowKey {
    uint32_t src = 0;
    uint32_t dst = 0;
    uint32_t sport = 0;
    uint32_t dport = 0;
    bool operator==(const FlowKey &other) const {
      return src == other.src && dst == other.dst && sport == other.sport && dport == other.dport;
    }
  };

  struct FlowInfo {
    uint32_t q_len = 0;
    uint32_t q_level = 0;
    uint32_t load_level = 0;
    uint32_t arn_type = 0;
    uint64_t ts = Simulator::Now().GetTimeStep();
  };

  enum ArnType { REMOTE_ARN = 0, REMOTE_CLEAR = 1, REMOTE_PERIOD = 2, LOCAL_ARN = 3, LOCAL_CLEAR = 4 };
  struct FlowKeyHash {
    size_t operator()(const FlowKey &key) const {
      size_t h = std::hash<uint32_t>{}(key.src);
      h ^= std::hash<uint32_t>{}(key.dst) + 0x9e3779b9 + (h << 6) + (h >> 2);
      h ^= std::hash<uint32_t>{}(key.sport) + 0x9e3779b9 + (h << 6) + (h >> 2);
      h ^= std::hash<uint32_t>{}(key.dport) + 0x9e3779b9 + (h << 6) + (h >> 2);
      return h;
    }
  };

  ArnHeader() = default;
  ArnHeader(FlowKey key, FlowInfo info) : m_flowKey(key), m_flowInfo(info) {}
  ArnHeader(uint32_t src, uint32_t dst, uint32_t sport, uint32_t dport,
            uint32_t qLen, uint32_t qLevel, uint32_t loadLevel,
            uint32_t arnType, uint64_t ts) {
    m_flowKey = {src, dst, sport, dport};
    m_flowInfo = {qLen, qLevel, loadLevel, arnType, ts};
  }

  FlowKey GetFlowKey() const { return m_flowKey; }
  FlowInfo GetFlowInfo() const { return m_flowInfo; }
  uint32_t GetSrc() const { return m_flowKey.src; }
  uint32_t GetDst() const { return m_flowKey.dst; }
  uint32_t GetSPort() const { return m_flowKey.sport; }
  uint32_t GetDPort() const { return m_flowKey.dport; }
  uint32_t GetQLen() const { return m_flowInfo.q_len; }
  uint32_t GetQLevel() const { return m_flowInfo.q_level; }
  uint32_t GetLoadLevel() const { return m_flowInfo.load_level; }
  uint32_t GetArnType() const { return m_flowInfo.arn_type; }
  uint64_t GetTs() const { return m_flowInfo.ts; }
  Time GetTsTime() const { return Time(m_flowInfo.ts); }
  void SetFlowKey(FlowKey key) { m_flowKey = key; }
  void SetFlowKey(uint32_t src, uint32_t dst, uint32_t sport, uint32_t dport) {
    m_flowKey = {src, dst, sport, dport};
  }
  void SetFlowInfo(FlowInfo info) { m_flowInfo = info; }
  void SetFlowInfo(uint32_t qLen, uint32_t qLevel, uint32_t loadLevel,
                   uint32_t arnType, uint64_t ts) {
    m_flowInfo = {qLen, qLevel, loadLevel, arnType, ts};
  }

  static TypeId GetTypeId();
  TypeId GetInstanceTypeId() const override { return GetTypeId(); }
  void Print(std::ostream &os) const override;
  uint32_t GetSerializedSize() const override { return GetHeaderSize(); }
  static uint32_t GetHeaderSize() { return sizeof(uint32_t) * 8 + sizeof(uint64_t); }
  void Serialize(Buffer::Iterator start) const override;
  uint32_t Deserialize(Buffer::Iterator start) override;

private:
  FlowKey m_flowKey;
  FlowInfo m_flowInfo;
};

} // namespace ns3

#endif
