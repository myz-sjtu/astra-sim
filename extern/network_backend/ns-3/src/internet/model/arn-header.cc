#include "arn-header.h"
#include "ns3/log.h"

namespace ns3 {
NS_LOG_COMPONENT_DEFINE("ArnHeader");
NS_OBJECT_ENSURE_REGISTERED(ArnHeader);

TypeId ArnHeader::GetTypeId() {
  static TypeId tid = TypeId("ns3::ArnHeader").SetParent<Header>().AddConstructor<ArnHeader>();
  return tid;
}

void ArnHeader::Print(std::ostream &os) const {
  os << "src=" << m_flowKey.src << " dst=" << m_flowKey.dst
     << " sport=" << m_flowKey.sport << " dport=" << m_flowKey.dport
     << " qlen=" << m_flowInfo.q_len << " qlevel=" << m_flowInfo.q_level
     << " load=" << m_flowInfo.load_level << " type=" << m_flowInfo.arn_type
     << " ts=" << m_flowInfo.ts;
}

void ArnHeader::Serialize(Buffer::Iterator start) const {
  start.WriteU32(m_flowKey.src);
  start.WriteU32(m_flowKey.dst);
  start.WriteU32(m_flowKey.sport);
  start.WriteU32(m_flowKey.dport);
  start.WriteU32(m_flowInfo.q_len);
  start.WriteU32(m_flowInfo.q_level);
  start.WriteU32(m_flowInfo.load_level);
  start.WriteU32(m_flowInfo.arn_type);
  start.WriteU64(m_flowInfo.ts);
}

uint32_t ArnHeader::Deserialize(Buffer::Iterator start) {
  m_flowKey.src = start.ReadU32();
  m_flowKey.dst = start.ReadU32();
  m_flowKey.sport = start.ReadU32();
  m_flowKey.dport = start.ReadU32();
  m_flowInfo.q_len = start.ReadU32();
  m_flowInfo.q_level = start.ReadU32();
  m_flowInfo.load_level = start.ReadU32();
  m_flowInfo.arn_type = start.ReadU32();
  m_flowInfo.ts = start.ReadU64();
  return GetHeaderSize();
}
} // namespace ns3
