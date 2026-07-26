#include "ns3/ipv4.h"
#include "ns3/packet.h"
#include "ns3/ipv4-header.h"
#include "ns3/arn-header.h"
#include "ns3/pause-header.h"
#include "ns3/flow-id-tag.h"
#include "ns3/boolean.h"
#include "ns3/uinteger.h"
#include "ns3/double.h"
#include "switch-node.h"
#include "qbb-net-device.h"
#include "ppp-header.h"
#include "ns3/simulator.h"
#include "ns3/int-header.h"
#include "ns3/random-variable-stream.h"
#include <cmath>
#include <iostream>
#include <limits>

namespace ns3 {

namespace {

const char* ArnTypeName(uint32_t arnType) {
	switch (arnType) {
	case ArnHeader::REMOTE_ARN:
		return "REMOTE_ARN";
	case ArnHeader::REMOTE_CLEAR:
		return "REMOTE_CLEAR";
	case ArnHeader::REMOTE_PERIOD:
		return "REMOTE_PERIOD";
	case ArnHeader::LOCAL_ARN:
		return "LOCAL_ARN";
	case ArnHeader::LOCAL_CLEAR:
		return "LOCAL_CLEAR";
	default:
		return "UNKNOWN_ARN";
	}
}

} // namespace

std::unordered_map<uint32_t, Ptr<Node> > SwitchNode::s_ipToLeafId;

TypeId SwitchNode::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::SwitchNode")
    .SetParent<Node> ()
    .AddConstructor<SwitchNode> ()
	.AddAttribute("EcnEnabled",
			"Enable ECN marking.",
			BooleanValue(false),
			MakeBooleanAccessor(&SwitchNode::m_ecnEnabled),
			MakeBooleanChecker())
	.AddAttribute("CcMode",
			"CC mode.",
			UintegerValue(0),
			MakeUintegerAccessor(&SwitchNode::m_ccMode),
			MakeUintegerChecker<uint32_t>())
	.AddAttribute("AckHighPrio",
			"Set high priority for ACK/NACK or not",
			UintegerValue(0),
			MakeUintegerAccessor(&SwitchNode::m_ackHighPrio),
			MakeUintegerChecker<uint32_t>())
	.AddAttribute("MaxRtt",
			"Max Rtt of the network",
			UintegerValue(9000),
			MakeUintegerAccessor(&SwitchNode::m_maxRtt),
			MakeUintegerChecker<uint32_t>())
	.AddAttribute("FlowStrategy",
			"Flow-based forwarding strategy (0=ECMP)",
			UintegerValue(0),
			MakeUintegerAccessor(&SwitchNode::m_flowStrategy),
			MakeUintegerChecker<uint32_t>())
	.AddAttribute("PacketStrategy",
			"Packet-based forwarding strategy when ARN is disabled (0=RoundRobin)",
			UintegerValue(0),
			MakeUintegerAccessor(&SwitchNode::m_packetStrategy),
			MakeUintegerChecker<uint32_t>())
	.AddAttribute("ArnPacketStrategy",
			"Packet-based forwarding strategy when ARN is enabled (0=ARN reject)",
			UintegerValue(0),
			MakeUintegerAccessor(&SwitchNode::m_arnPacketStrategy),
			MakeUintegerChecker<uint32_t>())
	.AddAttribute("ArnEnabled",
			"Enable ARN congestion notification for packet spray flows",
			BooleanValue(false),
			MakeBooleanAccessor(&SwitchNode::m_arn),
			MakeBooleanChecker())
	.AddAttribute("IsSpine",
			"Whether this switch is a spine switch",
			BooleanValue(false),
			MakeBooleanAccessor(&SwitchNode::m_isSpine),
			MakeBooleanChecker())
	.AddAttribute("IsLeaf",
			"Whether this switch is a leaf switch",
			BooleanValue(false),
			MakeBooleanAccessor(&SwitchNode::m_isLeaf),
			MakeBooleanChecker())
	.AddAttribute("ArnInterval",
			"Minimum interval between ARN notifications",
			TimeValue(Time::FromInteger(10000, Time::NS)),
			MakeTimeAccessor(&SwitchNode::m_arnInterval),
			MakeTimeChecker())
	.AddAttribute("CongestionQueueLength",
			"Queue length threshold in bytes for ARN trigger/clear",
			UintegerValue(5000000),
			MakeUintegerAccessor(&SwitchNode::m_congestionQlen),
			MakeUintegerChecker<uint64_t>())
  ;
  return tid;
}

SwitchNode::SwitchNode(){
	m_ecmpSeed = m_id;
	m_node_type = 1;
	m_mmu = CreateObject<SwitchMmu>();
	for (uint32_t i = 0; i < pCnt; i++)
		for (uint32_t j = 0; j < pCnt; j++)
			for (uint32_t k = 0; k < qCnt; k++)
				m_bytes[i][j][k] = 0;
	for (uint32_t i = 0; i < pCnt; i++)
		m_txBytes[i] = 0;
	for (uint32_t i = 0; i < pCnt; i++)
		m_lastPktSize[i] = m_lastPktTs[i] = 0;
	for (uint32_t i = 0; i < pCnt; i++)
		m_u[i] = 0;
	for (uint32_t i = 0; i < pCnt; i++)
		m_rrCounter[i] = 0;
	m_flowStrategy = 0;
	m_packetStrategy = 0;
	m_arnPacketStrategy = 0;
	m_arn = false;
	m_isSpine = false;
	m_isLeaf = false;
	m_congestionQlen = 5000000;
}

int SwitchNode::GetOutDev(Ptr<const Packet> p, CustomHeader &ch){
	// Dispatch based on forwarding mode in header
	if (ch.l3Prot == 0x11 && ch.udp.fwd_mode == 1) {
		// Packet spray mode
		if (m_arn) {
			switch (m_packetStrategy) {
				case PKT_STRATEGY_DLB:
					return GetOutDevRouteDlb(p, ch);
				case PKT_STRATEGY_RR:
				case PKT_STRATEGY_ARN_REJECT:
				default:
					return GetOutDevPktSprayArn(p, ch);
			}
		} else {
			switch (m_packetStrategy) {
				case PKT_STRATEGY_RR:
				default:
					return GetOutDevPktSprayRR(p, ch);
			}
		}
	} else {
		// Flow-based mode (default for UDP and all other protocols)
		switch (m_flowStrategy) {
			case FLOW_STRATEGY_ECMP:
			default:
				return GetOutDevFlowECMP(p, ch);
		}
	}
}

int SwitchNode::GetOutDevFlowECMP(Ptr<const Packet> p, CustomHeader &ch){
	// look up entries
	auto entry = m_rtTable.find(ch.dip);

	// no matching entry
	if (entry == m_rtTable.end())
		return -1;

	// entry found
	auto &nexthops = entry->second;

	// pick one next hop based on hash
	union {
		uint8_t u8[4+4+2+2];
		uint32_t u32[3];
	} buf;
	buf.u32[0] = ch.sip;
	buf.u32[1] = ch.dip;
	if (ch.l3Prot == 0x6)
		buf.u32[2] = ch.tcp.sport | ((uint32_t)ch.tcp.dport << 16);
	else if (ch.l3Prot == 0x11)
		buf.u32[2] = ch.udp.sport | ((uint32_t)ch.udp.dport << 16);
	else if (ch.l3Prot == 0xFC || ch.l3Prot == 0xFD)
		buf.u32[2] = ch.ack.sport | ((uint32_t)ch.ack.dport << 16);

	uint32_t idx = EcmpHash(buf.u8, 12, m_ecmpSeed) % nexthops.size();
	return nexthops[idx];
}

int SwitchNode::GetOutDevPktSprayRR(Ptr<const Packet> p, CustomHeader &ch){
	// look up entries
	auto entry = m_rtTable.find(ch.dip);

	// no matching entry
	if (entry == m_rtTable.end())
		return -1;

	// entry found
	auto &nexthops = entry->second;

	// get ingress port
	FlowIdTag t;
	uint32_t inDev = 0;
	if (p->PeekPacketTag(t))
		inDev = t.GetFlowId();

	// round-robin among nexthops
	uint32_t idx = m_rrCounter[inDev] % nexthops.size();
	m_rrCounter[inDev]++;
	return nexthops[idx];
}

bool SwitchNode::IsActiveArn(const ArnHeader::FlowInfo &flowInfo) const {
	return flowInfo.arn_type == ArnHeader::REMOTE_ARN ||
		flowInfo.arn_type == ArnHeader::REMOTE_PERIOD ||
		flowInfo.arn_type == ArnHeader::LOCAL_ARN;
}

uint32_t SwitchNode::GetArnPathCost(uint32_t dstLeafId, uint32_t outDev) const {
	auto receiveIt = m_arn_receive.find(dstLeafId);
	if (receiveIt == m_arn_receive.end()) {
		return 0;
	}

	const auto &profile = std::get<0>(receiveIt->second);
	auto profileIt = profile.find(outDev);
	if (profileIt == profile.end() || !IsActiveArn(profileIt->second)) {
		return 0;
	}

	const auto &effectTs = std::get<1>(receiveIt->second);
	const auto &clearTs = std::get<2>(receiveIt->second);
	auto effectIt = effectTs.find(outDev);
	auto clearIt = clearTs.find(outDev);
	if (clearIt != clearTs.end() &&
		(effectIt == effectTs.end() || clearIt->second >= effectIt->second)) {
		return 0;
	}

	return profileIt->second.q_level + 1;
}

int SwitchNode::GetOutDevPktSprayArn(Ptr<const Packet> p, CustomHeader &ch){
	auto entry = m_rtTable.find(ch.dip);
	if (entry == m_rtTable.end())
		return -1;

	auto &nexthops = entry->second;
	if (nexthops.empty())
		return -1;

	if (!IsLeafSwitch())
		return GetOutDevPktSprayRR(p, ch);

	Ptr<Node> dstLeaf;
	if (!ResolveLeafNode(ch.dip, dstLeaf) || dstLeaf == nullptr)
		return GetOutDevPktSprayRR(p, ch);

	uint32_t dstLeafId = dstLeaf->GetId();
	if (m_arn_receive.find(dstLeafId) == m_arn_receive.end())
		return GetOutDevPktSprayRR(p, ch);

	FlowIdTag t;
	uint32_t inDev = 0;
	if (p->PeekPacketTag(t))
		inDev = t.GetFlowId();

	uint32_t bestCost = std::numeric_limits<uint32_t>::max();
	std::vector<int> bestNexthops;
	for (int outDev : nexthops) {
		uint32_t cost = GetArnPathCost(dstLeafId, static_cast<uint32_t>(outDev));
		if (cost < bestCost) {
			bestCost = cost;
			bestNexthops.clear();
			bestNexthops.push_back(outDev);
		} else if (cost == bestCost) {
			bestNexthops.push_back(outDev);
		}
	}

	if (bestNexthops.empty())
		return GetOutDevPktSprayRR(p, ch);

	uint32_t idx = m_rrCounter[inDev] % bestNexthops.size();
	m_rrCounter[inDev]++;
	return bestNexthops[idx];
}

int SwitchNode::GetOutDevRouteDlb(Ptr<const Packet> p, CustomHeader &ch) {
	auto entry = m_rtTable.find(ch.dip);
	if (entry == m_rtTable.end()) {
		return -1;
	}

	auto &nexthops = entry->second;
	if (nexthops.empty()) {
		return -1;
	}

	int target = -1;
	double bestQuality = std::numeric_limits<double>::max();
	std::vector<int> goodNexthops;

	for (const auto &nexthop : nexthops) {
		ArnHeader::FlowInfo localFlowInfo;
		localFlowInfo.q_len = m_mmu->egress_bytes[nexthop][ch.udp.pg];
		localFlowInfo.q_level = GetQLevel(localFlowInfo.q_len);

		Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(m_devices[nexthop]);
		double load = dev == nullptr ? 0 : dev->calcBandwidth;
		localFlowInfo.load_level = GetLoadLevel(load);

		double totalQuality = localFlowInfo.load_level + localFlowInfo.q_level;
		if (totalQuality < bestQuality) {
			goodNexthops.clear();
			goodNexthops.emplace_back(nexthop);
			target = nexthop;
			bestQuality = totalQuality;
		} else if (std::abs(totalQuality - bestQuality) < 0.01) {
			goodNexthops.emplace_back(nexthop);
		}
	}

	if (goodNexthops.empty()) {
		return -1;
	}

	Ptr<UniformRandomVariable> rng = CreateObject<UniformRandomVariable>();
	uint32_t idx = rng->GetInteger(0, goodNexthops.size() - 1);
	target = goodNexthops[idx];
	return target;
}

void SwitchNode::CheckAndSendPfc(uint32_t inDev, uint32_t qIndex){
	Ptr<QbbNetDevice> device = DynamicCast<QbbNetDevice>(m_devices[inDev]);
	if (m_mmu->CheckShouldPause(inDev, qIndex)){
		device->SendPfc(qIndex, 0);
		m_mmu->SetPause(inDev, qIndex);
	}
}
void SwitchNode::CheckAndSendResume(uint32_t inDev, uint32_t qIndex){
	Ptr<QbbNetDevice> device = DynamicCast<QbbNetDevice>(m_devices[inDev]);
	if (m_mmu->CheckShouldResume(inDev, qIndex)){
		device->SendPfc(qIndex, 1);
		m_mmu->SetResume(inDev, qIndex);
	}
}

uint32_t SwitchNode::GetQLevel(uint64_t qlen) const {
	if (q_level.empty()) {
		return qlen > m_congestionQlen ? 1 : 0;
	}
	for (uint32_t i = 1; i < q_level.size(); i++) {
		if (qlen >= q_level[i - 1] && qlen < q_level[i]) {
			return i;
		}
	}
	return q_level.size();
}

uint32_t SwitchNode::GetLoadLevel(double load) const {
	if (load_level.empty()) {
		return 0;
	}
	for (uint32_t i = 1; i < load_level.size(); i++) {
		if (load >= load_level[i - 1] && load < load_level[i]) {
			return i;
		}
	}
	return load_level.size();
}

bool SwitchNode::ResolveLeafNode(uint32_t ip, Ptr<Node>& leafNode) const {
	auto it = m_ipToLeafId.find(ip);
	if (it != m_ipToLeafId.end() && it->second != nullptr) {
		leafNode = it->second;
		return true;
	}
	auto globalIt = s_ipToLeafId.find(ip);
	if (globalIt != s_ipToLeafId.end() && globalIt->second != nullptr) {
		leafNode = globalIt->second;
		return true;
	}
	return false;
}

bool SwitchNode::IsSpineIngress(uint32_t inDev) const {
	auto nodeIt = m_ifToNode.find(inDev);
	if (nodeIt == m_ifToNode.end() || nodeIt->second == nullptr) {
		return false;
	}
	return nodeIt->second->GetNodeType() != 0;
}

bool SwitchNode::HasHostNeighbor() const {
	for (const auto &entry : m_ifToNode) {
		if (entry.second != nullptr && entry.second->GetNodeType() == 0) {
			return true;
		}
	}
	return false;
}

bool SwitchNode::HasSwitchNeighbor() const {
	for (const auto &entry : m_ifToNode) {
		if (entry.second != nullptr && entry.second->GetNodeType() != 0) {
			return true;
		}
	}
	return false;
}

bool SwitchNode::IsSpineSwitch() {
	if (m_isSpine || GetNodeType() == 2) {
		return true;
	}
	if (m_isLeaf) {
		return false;
	}
	return HasSwitchNeighbor() && !HasHostNeighbor();
}

bool SwitchNode::IsLeafSwitch() {
	if (m_isLeaf) {
		return true;
	}
	if (m_isSpine || GetNodeType() == 2) {
		return false;
	}
	return HasHostNeighbor() || GetNodeType() == 1;
}

void SwitchNode::CheckAndSendArn(uint32_t inDev, uint32_t outDev, uint32_t qIndex, Ptr<Packet> p, CustomHeader &ch) {
	if (!m_arn || ch.l3Prot != 0x11 || ch.udp.fwd_mode != 1 || qIndex == 0) {
		return;
	}

	bool isSpine = IsSpineSwitch();
	bool isLeaf = !isSpine && IsLeafSwitch();

	if (isLeaf && IsSpineIngress(inDev)) {
		return;
	}

	Ptr<Node> srcLeaf;
	Ptr<Node> dstLeaf;
	bool hasLeafMapping = ResolveLeafNode(ch.sip, srcLeaf) && ResolveLeafNode(ch.dip, dstLeaf);
	if (!hasLeafMapping) {
		if (!isSpine) {
			return;
		}
		auto srcLeafIt = m_ifToNode.find(inDev);
		auto dstLeafIt = m_ifToNode.find(outDev);
		if (srcLeafIt == m_ifToNode.end() || dstLeafIt == m_ifToNode.end() ||
			srcLeafIt->second == nullptr || dstLeafIt->second == nullptr ||
			srcLeafIt->second->GetNodeType() == 0 || dstLeafIt->second->GetNodeType() == 0) {
			return;
		}
		srcLeaf = srcLeafIt->second;
		dstLeaf = dstLeafIt->second;
	}

	uint32_t srcIfId = inDev;
	uint32_t dstIfId = outDev;
	if (isSpine) {
		Ptr<SwitchNode> srcLeafSwitch = DynamicCast<SwitchNode>(srcLeaf);
		if (srcLeafSwitch == nullptr) {
			return;
		}
		auto srcIf = srcLeafSwitch->m_nodeToIf.find(GetId());
		if (srcIf == srcLeafSwitch->m_nodeToIf.end()) {
			return;
		}
		srcIfId = srcIf->second;
	}

	ArnHeader::FlowKey flowKey;
	flowKey.src = dstLeaf->GetId();
	flowKey.dst = srcLeaf->GetId();
	flowKey.sport = isSpine ? srcIfId : dstIfId;
	flowKey.dport = isSpine ? dstIfId : srcIfId;

	ArnHeader::FlowInfo flowInfo;
	flowInfo.q_len = m_mmu->egress_bytes[outDev][qIndex];
	flowInfo.q_level = GetQLevel(flowInfo.q_len);
	Ptr<QbbNetDevice> outDevice = DynamicCast<QbbNetDevice>(m_devices[outDev]);
	flowInfo.load_level = outDevice == nullptr ? 0 : GetLoadLevel(outDevice->calcBandwidth);
	flowInfo.ts = Simulator::Now().GetTimeStep();

	uint64_t clearThreshold = m_congestionQlen - (m_congestionQlen >> 3);
	uint64_t arnInterval = static_cast<uint64_t>(m_arnInterval.GetTimeStep());
	auto eventIt = m_arn_event.find(flowKey);
	uint32_t currentType = isSpine ? ArnHeader::REMOTE_CLEAR : ArnHeader::LOCAL_CLEAR;
	uint64_t lastTs = flowInfo.ts > arnInterval ? flowInfo.ts - arnInterval : 0;
	if (eventIt != m_arn_event.end()) {
		currentType = eventIt->second.arn_type;
		lastTs = eventIt->second.ts;
	}

	bool shouldTrigger = flowInfo.q_len > m_congestionQlen &&
		((isSpine && currentType == ArnHeader::REMOTE_CLEAR) ||
		 (isLeaf && currentType == ArnHeader::LOCAL_CLEAR) ||
		 flowInfo.ts - lastTs >= arnInterval) && p->GetSize() >= 1000;
	bool shouldClear = flowInfo.q_len < clearThreshold &&
		((isSpine && currentType == ArnHeader::REMOTE_ARN) ||
		 (isLeaf && currentType == ArnHeader::LOCAL_ARN)) && p->GetSize() >= 1000;

	if (!shouldTrigger && !shouldClear) {
		return;
	}

	Ptr<QbbNetDevice> device = DynamicCast<QbbNetDevice>(m_devices[inDev]);
	if (device == nullptr) {
		return;
	}

	if (isSpine) {
		flowInfo.arn_type = shouldTrigger ? ArnHeader::REMOTE_ARN : ArnHeader::REMOTE_CLEAR;
		m_arn_event[flowKey] = flowInfo;
		std::cout << "[ARN][send] time_ns=" << Simulator::Now().GetTimeStep()
				  << " switch=" << GetId()
				  << " role=spine"
				  << " type=" << ArnTypeName(flowInfo.arn_type)
				  << " trigger=" << shouldTrigger
				  << " clear=" << shouldClear
				  << " inDev=" << inDev
				  << " outDev=" << outDev
				  << " qIndex=" << qIndex
				  << " q_len=" << flowInfo.q_len
				  << " q_level=" << flowInfo.q_level
				  << " load_level=" << flowInfo.load_level
				  << " flowKey.srcLeaf=" << flowKey.src
				  << " flowKey.dstLeaf=" << flowKey.dst
				  << " flowKey.sport=" << flowKey.sport
				  << " flowKey.dport=" << flowKey.dport
				  << " pkt_sip=" << Ipv4Address(ch.sip)
				  << " pkt_dip=" << Ipv4Address(ch.dip)
				  << std::endl;
		device->SendArn(0, flowKey, flowInfo, ch);
		return;
	}

	if (isLeaf) {
		flowInfo.arn_type = shouldTrigger ? ArnHeader::LOCAL_ARN : ArnHeader::LOCAL_CLEAR;
		m_arn_event[flowKey] = flowInfo;
		std::cout << "[ARN][send] time_ns=" << Simulator::Now().GetTimeStep()
				  << " switch=" << GetId()
				  << " role=leaf"
				  << " type=" << ArnTypeName(flowInfo.arn_type)
				  << " trigger=" << shouldTrigger
				  << " clear=" << shouldClear
				  << " inDev=" << inDev
				  << " outDev=" << outDev
				  << " qIndex=" << qIndex
				  << " q_len=" << flowInfo.q_len
				  << " q_level=" << flowInfo.q_level
				  << " load_level=" << flowInfo.load_level
				  << " flowKey.srcLeaf=" << flowKey.src
				  << " flowKey.dstLeaf=" << flowKey.dst
				  << " flowKey.sport=" << flowKey.sport
				  << " flowKey.dport=" << flowKey.dport
				  << " pkt_sip=" << Ipv4Address(ch.sip)
				  << " pkt_dip=" << Ipv4Address(ch.dip)
				  << std::endl;
		CustomHeader arnCh = ch;
		Ptr<Packet> arnPacket = device->ArnHeaderProcess(flowKey, flowInfo, arnCh);
		SwitchReceiveArn(device, arnPacket, arnCh, outDev);
	}
}

bool SwitchNode::SwitchReceiveArn(Ptr<NetDevice> device, Ptr<Packet> packet, CustomHeader &ch, uint32_t congestedPath) {
	if (!m_arn) {
		return true;
	}

	bool isSpine = IsSpineSwitch();
	bool isLeaf = !isSpine && IsLeafSwitch();
	if (!isLeaf || ch.l3Prot != 0xFA) {
		return true;
	}

	ArnHeader::FlowInfo flowInfo;
	flowInfo.q_len = ch.arn.flowInfo.qlen;
	flowInfo.q_level = ch.arn.flowInfo.q_level;
	flowInfo.load_level = ch.arn.flowInfo.load_level;
	flowInfo.arn_type = ch.arn.flowInfo.arn_type;
	flowInfo.ts = ch.arn.flowInfo.ts;

	uint32_t dstLeafId = ch.arn.flowKey.src;
	std::get<0>(m_arn_receive[dstLeafId])[congestedPath] = flowInfo;

	if (flowInfo.arn_type == ArnHeader::REMOTE_ARN || flowInfo.arn_type == ArnHeader::LOCAL_ARN) {
		std::get<1>(m_arn_receive[dstLeafId])[congestedPath] = Simulator::Now().GetTimeStep();
	} else if (flowInfo.arn_type == ArnHeader::REMOTE_CLEAR || flowInfo.arn_type == ArnHeader::LOCAL_CLEAR) {
		std::get<2>(m_arn_receive[dstLeafId])[congestedPath] = Simulator::Now().GetTimeStep();
	}

	std::cout << "[ARN][source-leaf-read] time_ns=" << Simulator::Now().GetTimeStep()
			  << " switch=" << GetId()
			  << " congestedPath=" << congestedPath
			  << " type=" << ArnTypeName(flowInfo.arn_type)
			  << " q_len=" << flowInfo.q_len
			  << " q_level=" << flowInfo.q_level
			  << " load_level=" << flowInfo.load_level
			  << " event_ts=" << flowInfo.ts
			  << " flowKey.srcLeaf=" << ch.arn.flowKey.src
			  << " flowKey.dstLeaf=" << ch.arn.flowKey.dst
			  << " flowKey.sport=" << ch.arn.flowKey.sport
			  << " flowKey.dport=" << ch.arn.flowKey.dport
			  << " pkt_sip=" << Ipv4Address(ch.sip)
			  << " pkt_dip=" << Ipv4Address(ch.dip)
			  << std::endl;

	return true;
}

void SwitchNode::SendToDev(Ptr<Packet>p, CustomHeader &ch){
	int idx = GetOutDev(p, ch);
	if (idx >= 0){
		NS_ASSERT_MSG(m_devices[idx]->IsLinkUp(), "The routing table look up should return link that is up");

		// determine the qIndex
		uint32_t qIndex;
		if (ch.l3Prot == 0xFF || ch.l3Prot == 0xFE || ch.l3Prot == 0xFA || (m_ackHighPrio && (ch.l3Prot == 0xFD || ch.l3Prot == 0xFC))){  //QCN, PFC, ARN or NACK, go highest priority
			qIndex = 0;
		}else{
			qIndex = (ch.l3Prot == 0x06 ? 1 : ch.udp.pg); // if TCP, put to queue 1
		}

		// admission control
		FlowIdTag t;
		p->PeekPacketTag(t);
		uint32_t inDev = t.GetFlowId();
		if (qIndex != 0){ //not highest priority
			if (m_mmu->CheckIngressAdmission(inDev, qIndex, p->GetSize()) && m_mmu->CheckEgressAdmission(idx, qIndex, p->GetSize())){			// Admission control
				m_mmu->UpdateIngressAdmission(inDev, qIndex, p->GetSize());
				m_mmu->UpdateEgressAdmission(idx, qIndex, p->GetSize());
			}else{
				return; // Drop
			}
			CheckAndSendPfc(inDev, qIndex);
			CheckAndSendArn(inDev, idx, qIndex, p, ch);
		}
		m_bytes[inDev][idx][qIndex] += p->GetSize();
		m_devices[idx]->SwitchSend(qIndex, p, ch);
	}else
	{
		return; // Drop
	}
}

uint32_t SwitchNode::EcmpHash(const uint8_t* key, size_t len, uint32_t seed) {
  uint32_t h = seed;
  if (len > 3) {
    const uint32_t* key_x4 = (const uint32_t*) key;
    size_t i = len >> 2;
    do {
      uint32_t k = *key_x4++;
      k *= 0xcc9e2d51;
      k = (k << 15) | (k >> 17);
      k *= 0x1b873593;
      h ^= k;
      h = (h << 13) | (h >> 19);
      h += (h << 2) + 0xe6546b64;
    } while (--i);
    key = (const uint8_t*) key_x4;
  }
  if (len & 3) {
    size_t i = len & 3;
    uint32_t k = 0;
    key = &key[i - 1];
    do {
      k <<= 8;
      k |= *key--;
    } while (--i);
    k *= 0xcc9e2d51;
    k = (k << 15) | (k >> 17);
    k *= 0x1b873593;
    h ^= k;
  }
  h ^= len;
  h ^= h >> 16;
  h *= 0x85ebca6b;
  h ^= h >> 13;
  h *= 0xc2b2ae35;
  h ^= h >> 16;
  return h;
}

void SwitchNode::SetEcmpSeed(uint32_t seed){
	m_ecmpSeed = seed;
}

void SwitchNode::AddTableEntry(Ipv4Address &dstAddr, uint32_t intf_idx){
	uint32_t dip = dstAddr.Get();
	m_rtTable[dip].push_back(intf_idx);
}

void SwitchNode::AddNodeEntry(uint32_t intf_idx, Ptr<Node> node) {
	if (m_ifToNode.find(intf_idx) == m_ifToNode.end()) {
		m_ifToNode[intf_idx] = node;
	}
	if (node != nullptr && m_nodeToIf.find(node->GetId()) == m_nodeToIf.end()) {
		m_nodeToIf[node->GetId()] = intf_idx;
	}
	if (node != nullptr && node->GetNodeType() == 0) {
		uint32_t hostId = node->GetId();
		uint32_t astraHostIp = 0x0b000001 + ((hostId / 256) * 0x00010000) + ((hostId % 256) * 0x00000100);
		Ptr<Node> leaf = GetObject<Node>();
		m_ipToLeafId[astraHostIp] = leaf;
		s_ipToLeafId[astraHostIp] = leaf;

		Ptr<Ipv4> ipv4 = node->GetObject<Ipv4>();
		if (ipv4 != nullptr && ipv4->GetNInterfaces() > 1 && ipv4->GetNAddresses(1) > 0) {
			uint32_t ip = ipv4->GetAddress(1, 0).GetLocal().Get();
			m_ipToLeafId[ip] = leaf;
			s_ipToLeafId[ip] = leaf;
		}
	}
}

void SwitchNode::AddInterfaceEntry(uint32_t node_id, uint32_t intf_idx) {
	if (m_nodeToIf.find(node_id) == m_nodeToIf.end()) {
		m_nodeToIf[node_id] = intf_idx;
	}
}

void SwitchNode::ClearTable(){
	m_rtTable.clear();
}

// This function can only be called in switch mode
bool SwitchNode::SwitchReceiveFromDevice(Ptr<NetDevice> device, Ptr<Packet> packet, CustomHeader &ch){
	if (ch.l3Prot == 0xFA) {
		FlowIdTag t;
		uint32_t inDev = 0;
		if (packet->PeekPacketTag(t)) {
			inDev = t.GetFlowId();
		}
		return SwitchReceiveArn(device, packet, ch, inDev);
	}
	SendToDev(packet, ch);
	return true;
}

void SwitchNode::SwitchNotifyDequeue(uint32_t ifIndex, uint32_t qIndex, Ptr<Packet> p){
	FlowIdTag t;
	p->PeekPacketTag(t);
	if (qIndex != 0){
		uint32_t inDev = t.GetFlowId();
		m_mmu->RemoveFromIngressAdmission(inDev, qIndex, p->GetSize());
		m_mmu->RemoveFromEgressAdmission(ifIndex, qIndex, p->GetSize());
		m_bytes[inDev][ifIndex][qIndex] -= p->GetSize();
		if (m_ecnEnabled){
			bool egressCongested = m_mmu->ShouldSendCN(ifIndex, qIndex);
			if (egressCongested){
				PppHeader ppp;
				Ipv4Header h;
				p->RemoveHeader(ppp);
				p->RemoveHeader(h);
				h.SetEcn((Ipv4Header::EcnType)0x03);
				p->AddHeader(h);
				p->AddHeader(ppp);
			}
		}
		//CheckAndSendPfc(inDev, qIndex);
		CheckAndSendResume(inDev, qIndex);
	}
	if (1){
		uint8_t* buf = p->GetBuffer();
		if (buf[PppHeader::GetStaticSize() + 9] == 0x11){ // udp packet
			IntHeader *ih = (IntHeader*)&buf[PppHeader::GetStaticSize() + 20 + 8 + 7]; // ppp, ip, udp, SeqTs(4+2+1), INT
			Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(m_devices[ifIndex]);
			if (m_ccMode == 3){ // HPCC
				ih->PushHop(Simulator::Now().GetTimeStep(), m_txBytes[ifIndex], dev->GetQueue()->GetNBytesTotal(), dev->GetDataRate().GetBitRate());
			}else if (m_ccMode == 10){ // HPCC-PINT
				uint64_t t = Simulator::Now().GetTimeStep();
				uint64_t dt = t - m_lastPktTs[ifIndex];
				if (dt > m_maxRtt)
					dt = m_maxRtt;
				uint64_t B = dev->GetDataRate().GetBitRate() / 8; //Bps
				uint64_t qlen = dev->GetQueue()->GetNBytesTotal();
				double newU;

				/**************************
				 * approximate calc
				 *************************/
				int b = 20, m = 16, l = 20; // see log2apprx's paremeters
				int sft = logres_shift(b,l);
				double fct = 1<<sft; // (multiplication factor corresponding to sft)
				double log_T = log2(m_maxRtt)*fct; // log2(T)*fct
				double log_B = log2(B)*fct; // log2(B)*fct
				double log_1e9 = log2(1e9)*fct; // log2(1e9)*fct
				double qterm = 0;
				double byteTerm = 0;
				double uTerm = 0;
				if ((qlen >> 8) > 0){
					int log_dt = log2apprx(dt, b, m, l); // ~log2(dt)*fct
					int log_qlen = log2apprx(qlen >> 8, b, m, l); // ~log2(qlen / 256)*fct
					qterm = pow(2, (
								log_dt + log_qlen + log_1e9 - log_B - 2*log_T
								)/fct
							) * 256;
					// 2^((log2(dt)*fct+log2(qlen/256)*fct+log2(1e9)*fct-log2(B)*fct-2*log2(T)*fct)/fct)*256 ~= dt*qlen*1e9/(B*T^2)
				}
				if (m_lastPktSize[ifIndex] > 0){
					int byte = m_lastPktSize[ifIndex];
					int log_byte = log2apprx(byte, b, m, l);
					byteTerm = pow(2, (
								log_byte + log_1e9 - log_B - log_T
								)/fct
							);
					// 2^((log2(byte)*fct+log2(1e9)*fct-log2(B)*fct-log2(T)*fct)/fct) ~= byte*1e9 / (B*T)
				}
				if (m_maxRtt > dt && m_u[ifIndex] > 0){
					int log_T_dt = log2apprx(m_maxRtt - dt, b, m, l); // ~log2(T-dt)*fct
					int log_u = log2apprx(int(round(m_u[ifIndex] * 8192)), b, m, l); // ~log2(u*512)*fct
					uTerm = pow(2, (
								log_T_dt + log_u - log_T
								)/fct
							) / 8192;
					// 2^((log2(T-dt)*fct+log2(u*512)*fct-log2(T)*fct)/fct)/512 = (T-dt)*u/T
				}
				newU = qterm+byteTerm+uTerm;

				#if 0
				/**************************
				 * accurate calc
				 *************************/
				double weight_ewma = double(dt) / m_maxRtt;
				double u;
				if (m_lastPktSize[ifIndex] == 0)
					u = 0;
				else{
					double txRate = m_lastPktSize[ifIndex] / double(dt); // B/ns
					u = (qlen / m_maxRtt + txRate) * 1e9 / B;
				}
				newU = m_u[ifIndex] * (1 - weight_ewma) + u * weight_ewma;
				printf(" %lf\n", newU);
				#endif

				/************************
				 * update PINT header
				 ***********************/
				uint16_t power = Pint::encode_u(newU);
				if (power > ih->GetPower())
					ih->SetPower(power);

				m_u[ifIndex] = newU;
			}
		}
	}
	m_txBytes[ifIndex] += p->GetSize();
	m_lastPktSize[ifIndex] = p->GetSize();
	m_lastPktTs[ifIndex] = Simulator::Now().GetTimeStep();
}

int SwitchNode::logres_shift(int b, int l){
	static int data[] = {0,0,1,2,2,3,3,3,3,4,4,4,4,4,4,4,4,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5};
	return l - data[b];
}

int SwitchNode::log2apprx(int x, int b, int m, int l){
	int x0 = x;
	int msb = int(log2(x)) + 1;
	if (msb > m){
		x = (x >> (msb - m) << (msb - m));
		#if 0
		x += + (1 << (msb - m - 1));
		#else
		int mask = (1 << (msb-m)) - 1;
		if ((x0 & mask) > (rand() & mask))
			x += 1<<(msb-m);
		#endif
	}
	return int(log2(x) * (1<<logres_shift(b, l)));
}

} /* namespace ns3 */
