#include "arn-header.h"

#include "ns3/log.h"

namespace ns3 {

NS_LOG_COMPONENT_DEFINE("ArnHeader");
NS_OBJECT_ENSURE_REGISTERED(ArnHeader);

ArnHeader::ArnHeader() = default;

ArnHeader::ArnHeader(FlowKey flowKey, FlowInfo flowInfo) : m_flowKey(flowKey), m_flowInfo(flowInfo) {}

ArnHeader::ArnHeader(uint32_t src,
                     uint32_t dst,
                     uint32_t sport,
                     uint32_t dport,
                     uint32_t qLen,
                     uint32_t qLevel,
                     uint32_t loadLevel,
                     uint32_t arnType,
                     uint64_t ts) {
    SetFlowKey(src, dst, sport, dport);
    SetFlowInfo(qLen, qLevel, loadLevel, arnType, ts);
}

ArnHeader::FlowKey ArnHeader::GetFlowKey() const { return m_flowKey; }

ArnHeader::FlowInfo ArnHeader::GetFlowInfo() const { return m_flowInfo; }

uint32_t ArnHeader::GetSrc() const { return m_flowKey.src; }

uint32_t ArnHeader::GetDst() const { return m_flowKey.dst; }

uint32_t ArnHeader::GetSPort() const { return m_flowKey.sport; }

uint32_t ArnHeader::GetDPort() const { return m_flowKey.dport; }

uint32_t ArnHeader::GetQLen() const { return m_flowInfo.q_len; }

uint32_t ArnHeader::GetQLevel() const { return m_flowInfo.q_level; }

uint32_t ArnHeader::GetLoadLevel() const { return m_flowInfo.load_level; }

uint32_t ArnHeader::GetArnType() const { return m_flowInfo.arn_type; }

uint64_t ArnHeader::GetTs() const { return m_flowInfo.ts; }

Time ArnHeader::GetTsTime() const { return Time(m_flowInfo.ts); }

void ArnHeader::SetFlowKey(FlowKey flowKey) { m_flowKey = flowKey; }

void ArnHeader::SetFlowKey(uint32_t src, uint32_t dst, uint32_t sport, uint32_t dport) {
    m_flowKey.src = src;
    m_flowKey.dst = dst;
    m_flowKey.sport = sport;
    m_flowKey.dport = dport;
}

void ArnHeader::SetFlowInfo(FlowInfo flowInfo) { m_flowInfo = flowInfo; }

void ArnHeader::SetFlowInfo(uint32_t qLen,
                            uint32_t qLevel,
                            uint32_t loadLevel,
                            uint32_t arnType,
                            uint64_t ts) {
    m_flowInfo.q_len = qLen;
    m_flowInfo.q_level = qLevel;
    m_flowInfo.load_level = loadLevel;
    m_flowInfo.arn_type = arnType;
    m_flowInfo.ts = ts;
}

TypeId ArnHeader::GetTypeId() {
    static TypeId tid = TypeId("ns3::ArnHeader").SetParent<Header>().AddConstructor<ArnHeader>();
    return tid;
}

TypeId ArnHeader::GetInstanceTypeId() const { return GetTypeId(); }

void ArnHeader::Print(std::ostream& os) const {
    os << "flowKey: { src: " << m_flowKey.src << " dst: " << m_flowKey.dst
       << " sport: " << m_flowKey.sport << " dport: " << m_flowKey.dport
       << " } flowInfo: { q_len: " << m_flowInfo.q_len << " q_level: " << m_flowInfo.q_level
       << " load_level: " << m_flowInfo.load_level << " arn_type: " << m_flowInfo.arn_type
       << " ts: " << m_flowInfo.ts << " }";
}

uint32_t ArnHeader::GetSerializedSize() const { return GetHeaderSize(); }

uint32_t ArnHeader::GetHeaderSize() {
    return sizeof(uint32_t) * 8 + sizeof(uint64_t);
}

void ArnHeader::Serialize(Buffer::Iterator start) const {
    Buffer::Iterator i = start;
    i.WriteU32(m_flowKey.src);
    i.WriteU32(m_flowKey.dst);
    i.WriteU32(m_flowKey.sport);
    i.WriteU32(m_flowKey.dport);
    i.WriteU32(m_flowInfo.q_len);
    i.WriteU32(m_flowInfo.q_level);
    i.WriteU32(m_flowInfo.load_level);
    i.WriteU32(m_flowInfo.arn_type);
    i.WriteU64(m_flowInfo.ts);
}

uint32_t ArnHeader::Deserialize(Buffer::Iterator start) {
    Buffer::Iterator i = start;
    m_flowKey.src = i.ReadU32();
    m_flowKey.dst = i.ReadU32();
    m_flowKey.sport = i.ReadU32();
    m_flowKey.dport = i.ReadU32();
    m_flowInfo.q_len = i.ReadU32();
    m_flowInfo.q_level = i.ReadU32();
    m_flowInfo.load_level = i.ReadU32();
    m_flowInfo.arn_type = i.ReadU32();
    m_flowInfo.ts = i.ReadU64();
    return GetSerializedSize();
}

} // namespace ns3
