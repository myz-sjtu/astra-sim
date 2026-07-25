#ifndef ARN_HEADER_H_
#define ARN_HEADER_H_

#include "ns3/header.h"
#include "ns3/nstime.h"
#include "ns3/simulator.h"
#include "ns3/type-id.h"

#include <cstdint>
#include <functional>

namespace ns3 {

class ArnHeader : public Header {
public:
    struct FlowKey {
        uint32_t src;
        uint32_t dst;
        uint32_t sport;
        uint32_t dport;

        FlowKey() : src(0), dst(0), sport(0), dport(0) {}

        bool operator==(const FlowKey& other) const {
            return src == other.src && dst == other.dst && sport == other.sport && dport == other.dport;
        }
    };

    struct FlowInfo {
        uint32_t q_len;
        uint32_t q_level;
        uint32_t load_level;
        uint32_t arn_type;
        uint64_t ts;

        FlowInfo()
            : q_len(0), q_level(0), load_level(0), arn_type(0), ts(Simulator::Now().GetTimeStep()) {}
    };

    enum ArnType {
        REMOTE_ARN = 0,
        REMOTE_CLEAR,
        REMOTE_PERIOD,
        LOCAL_ARN,
        LOCAL_CLEAR
    };

    struct FlowKeyHash {
        size_t operator()(const FlowKey& key) const {
            return std::hash<uint32_t>()(key.src) ^ std::hash<uint32_t>()(key.dst) ^
                   std::hash<uint32_t>()(key.sport) ^ std::hash<uint32_t>()(key.dport);
        }
    };

    ArnHeader();
    ArnHeader(FlowKey flowKey, FlowInfo flowInfo);
    ArnHeader(uint32_t src,
              uint32_t dst,
              uint32_t sport,
              uint32_t dport,
              uint32_t qLen,
              uint32_t qLevel,
              uint32_t loadLevel,
              uint32_t arnType,
              uint64_t ts);

    FlowKey GetFlowKey() const;
    FlowInfo GetFlowInfo() const;
    uint32_t GetSrc() const;
    uint32_t GetDst() const;
    uint32_t GetSPort() const;
    uint32_t GetDPort() const;
    uint32_t GetQLen() const;
    uint32_t GetQLevel() const;
    uint32_t GetLoadLevel() const;
    uint32_t GetArnType() const;
    uint64_t GetTs() const;
    Time GetTsTime() const;

    void SetFlowKey(FlowKey flowKey);
    void SetFlowKey(uint32_t src, uint32_t dst, uint32_t sport, uint32_t dport);
    void SetFlowInfo(FlowInfo flowInfo);
    void SetFlowInfo(uint32_t qLen, uint32_t qLevel, uint32_t loadLevel, uint32_t arnType, uint64_t ts);

    static TypeId GetTypeId();
    TypeId GetInstanceTypeId() const override;
    void Print(std::ostream& os) const override;
    uint32_t GetSerializedSize() const override;
    static uint32_t GetHeaderSize();
    void Serialize(Buffer::Iterator start) const override;
    uint32_t Deserialize(Buffer::Iterator start) override;

private:
    FlowKey m_flowKey;
    FlowInfo m_flowInfo;
};

} // namespace ns3

#endif // ARN_HEADER_H_
