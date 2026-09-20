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
#include <cmath>
#include <algorithm>
#include <limits>
#include <utility>

namespace ns3 {

std::unordered_map<uint32_t, Ptr<Node> > g_arnIpToLeaf;

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
			"Flow-based forwarding strategy (0=ECMP, 1=PathPinning)",
			UintegerValue(0),
			MakeUintegerAccessor(&SwitchNode::m_flowStrategy),
			MakeUintegerChecker<uint32_t>())
	.AddAttribute("PacketStrategy",
			"Packet-based forwarding strategy (0=FlowBaseRoundRobin, 1=Random, 2=DLB)",
			UintegerValue(0),
			MakeUintegerAccessor(&SwitchNode::m_packetStrategy),
			MakeUintegerChecker<uint32_t>(0, 2))
	.AddAttribute("ArnPacketStrategy", "ARN packet strategy (3=GLB)",
			UintegerValue(ARN_PKT_STRATEGY_GLB),
			MakeUintegerAccessor(&SwitchNode::m_arnPacketStrategy),
			MakeUintegerChecker<uint32_t>())
	.AddAttribute("ArnEnabled", "Enable ARN congestion notifications",
			BooleanValue(false), MakeBooleanAccessor(&SwitchNode::m_arn), MakeBooleanChecker())
	.AddAttribute("IsLeaf", "Whether this is a leaf switch", BooleanValue(false),
			MakeBooleanAccessor(&SwitchNode::m_isLeaf), MakeBooleanChecker())
	.AddAttribute("IsSpine", "Whether this is a spine switch", BooleanValue(false),
			MakeBooleanAccessor(&SwitchNode::m_isSpine), MakeBooleanChecker())
	.AddAttribute("ArnInterval", "Minimum ARN notification interval",
			TimeValue(NanoSeconds(10000)), MakeTimeAccessor(&SwitchNode::m_arnInterval), MakeTimeChecker())
	.AddAttribute("CongestionQueueLength", "ARN queue threshold in bytes",
			UintegerValue(5000000), MakeUintegerAccessor(&SwitchNode::m_congestionQlen),
			MakeUintegerChecker<uint64_t>())
	.AddAttribute("ArnTrace", "Enable verbose ARN route logging", BooleanValue(false),
			MakeBooleanAccessor(&SwitchNode::m_arnTrace), MakeBooleanChecker())
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
	m_pktSprayRandom = CreateObject<UniformRandomVariable>();
	m_flowStrategy = 0;
	m_packetStrategy = 0;
	m_arnPacketStrategy = ARN_PKT_STRATEGY_GLB;
	m_arn = false;
	m_isSpine = false;
	m_isLeaf = false;
	m_arnInterval = NanoSeconds(10000);
	m_congestionQlen = 5000000;
	m_arnTrace = false;
	m_dropCnt = 0;
}

int SwitchNode::GetOutDev(Ptr<const Packet> p, CustomHeader &ch){
	if (ch.l3Prot == 0xFA) {
		// Control packets are routed by the reverse ECMP route, even when data
		// uses path pinning.
		return GetOutDevFlowECMP(p, ch);
	}
	// Dispatch based on forwarding mode in header
	if (ch.l3Prot == 0x11 && ch.udp.fwd_mode == 1) {
		// Packet spray mode
		if (m_arn && m_arnPacketStrategy == ARN_PKT_STRATEGY_GLB)
			return GetOutDevRouteGlb(p, ch);
		switch (m_packetStrategy) {
			case PKT_STRATEGY_DLB:
				return GetOutDevPktSprayDlb(p, ch);
			case PKT_STRATEGY_RANDOM:
				return GetOutDevPktSprayRandom(p, ch);
			case PKT_STRATEGY_RR:
			default:
				return GetOutDevPktSprayRR(p, ch);
		}
	} else {
		// Flow-based mode (default for UDP and all other protocols)
		switch (m_flowStrategy) {
			case FLOW_STRATEGY_PATH_PINNING:
				return GetOutDevPathPinning(p, ch);
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
	else if (ch.l3Prot == 0xFA)
		buf.u32[2] = ch.arn.flowKey.sport ^ (ch.arn.flowKey.dport << 16);

	uint32_t idx = EcmpHash(buf.u8, 12, m_ecmpSeed) % nexthops.size();
	return nexthops[idx];
}

int SwitchNode::GetInDev(Ptr<const Packet> p) {
	FlowIdTag t;
	if (p->PeekPacketTag(t))
		return t.GetFlowId();
	return 0;
}

int SwitchNode::GetOutDevPathPinning(Ptr<const Packet> p, CustomHeader &ch){
	auto entry = m_rtTable.find(ch.dip);
	if (entry == m_rtTable.end())
		return -1;

	auto &nexthops = entry->second;
	int n = nexthops.size();
	if (n == 0)
		return -1;

	if (n == 1)
		return nexthops[0];
	// In fact, modulo window should be n, rather than max(n,8). Existing implementation could lead to unfairness when muti-link breaks down.
	// Keep it unchanged to be consistent with former result and collision pattern.

	static const int kPathPinningModuloMinWindow = 8;
	int moduloWindow = n > kPathPinningModuloMinWindow ? n : kPathPinningModuloMinWindow;
	/* int moduloWindow = n; */
	int idx = (GetInDev(p) - 1) % moduloWindow;
	if (idx < 0)
		idx += moduloWindow;

	for (int i = 0; i < moduloWindow; i++) {
		if (idx < n && this->GetDevice(nexthops[idx])->IsLinkUp())
			return nexthops[idx];
		idx = (idx + 1) % moduloWindow;
	}

	return -1;
}

int SwitchNode::GetOutDevPktSprayRR(Ptr<const Packet> p, CustomHeader &ch){
	// look up entries
	auto entry = m_rtTable.find(ch.dip);

	// no matching entry
	if (entry == m_rtTable.end())
		return -1;

	// entry found
	auto &nexthops = entry->second;
	if (nexthops.empty())
		return -1;

	uint32_t inDev = GetInDev(p);

	uint32_t idx = (m_rrCounter[inDev]) % nexthops.size();
	m_rrCounter[inDev]++;
	return nexthops[idx];
}

int SwitchNode::GetOutDevPktSprayRandom(Ptr<const Packet> p, CustomHeader &ch){
	(void)p;

	// look up entries
	auto entry = m_rtTable.find(ch.dip);

	// no matching entry
	if (entry == m_rtTable.end())
		return -1;

	// entry found
	auto &nexthops = entry->second;
	if (nexthops.empty())
		return -1;

	uint32_t idx = m_pktSprayRandom->GetInteger(0, static_cast<uint32_t>(nexthops.size() - 1));
	return nexthops[idx];
}

int SwitchNode::GetOutDevPktSprayDlb(Ptr<const Packet> p, CustomHeader &ch){
	(void)p;

	auto entry = m_rtTable.find(ch.dip);
	if (entry == m_rtTable.end())
		return -1;

	auto &nexthops = entry->second;
	if (nexthops.empty() || ch.udp.pg >= qCnt)
		return -1;

	std::vector<std::pair<uint32_t, int> > candidates;
	candidates.reserve(nexthops.size());
	for (const auto &nexthop : nexthops) {
		if (nexthop < 0 || static_cast<uint32_t>(nexthop) >= pCnt)
			continue;
		uint32_t queueBytes = m_mmu->egress_bytes[static_cast<uint32_t>(nexthop)][ch.udp.pg];
		candidates.push_back(std::make_pair(queueBytes, nexthop));
	}

	if (candidates.empty())
		return -1;

	std::sort(candidates.begin(), candidates.end(),
			[](const std::pair<uint32_t, int> &a, const std::pair<uint32_t, int> &b) {
				if (a.first != b.first)
					return a.first < b.first;
				return a.second < b.second;
			});

	uint32_t bestHalf = static_cast<uint32_t>((candidates.size() + 1) / 2);
	uint32_t idx = m_pktSprayRandom->GetInteger(0, bestHalf - 1);
	return candidates[idx].second;
}

uint32_t SwitchNode::GetQLevel(uint64_t qlen) const {
	if (q_level.empty()) return qlen > m_congestionQlen ? 1 : 0;
	for (uint32_t i = 1; i < q_level.size(); ++i)
		if (qlen >= q_level[i - 1] && qlen < q_level[i]) return i;
	return static_cast<uint32_t>(q_level.size());
}

uint32_t SwitchNode::GetLoadLevel(double load) const {
	if (load_level.empty()) return 0;
	for (uint32_t i = 1; i < load_level.size(); ++i)
		if (load >= load_level[i - 1] && load < load_level[i]) return i;
	return static_cast<uint32_t>(load_level.size());
}

uint32_t SwitchNode::GetArnPathQuality(uint32_t dstLeafId, uint32_t outDev,
																	 uint32_t *qLevel,
																	 uint32_t *loadLevel) const {
	if (qLevel) *qLevel = 0;
	if (loadLevel) *loadLevel = 0;
	auto receiveIt = m_arn_receive.find(dstLeafId);
	if (receiveIt == m_arn_receive.end()) return 0;
	const auto &profile = std::get<0>(receiveIt->second);
	auto profileIt = profile.find(outDev);
	if (profileIt == profile.end()) return 0;
	const ArnHeader::FlowInfo &info = profileIt->second;
	if (info.arn_type != ArnHeader::REMOTE_ARN && info.arn_type != ArnHeader::REMOTE_PERIOD) return 0;
	/* uint64_t now = Simulator::Now().GetTimeStep();
	uint64_t interval = static_cast<uint64_t>(m_arnInterval.GetTimeStep());
	uint64_t maxAge = std::max<uint64_t>(5 * m_maxRtt, 5 * interval);
	if (now < info.ts || now - info.ts > maxAge) return 0; */
	const auto &clearTs = std::get<2>(receiveIt->second);
	auto clearIt = clearTs.find(outDev);
	if (clearIt != clearTs.end() && clearIt->second >= info.ts) return 0;
	if (qLevel) *qLevel = info.q_level;
	if (loadLevel) *loadLevel = info.load_level;
	return info.q_level + info.load_level;
}

int SwitchNode::GetOutDevRouteGlb(Ptr<const Packet> p, CustomHeader &ch) {
	auto entry = m_rtTable.find(ch.dip);
	if (entry == m_rtTable.end() || entry->second.empty()) return -1;
	if (!m_arn || !IsLeafSwitch()) return GetOutDevPktSprayDlb(p, ch);
	Ptr<Node> dstLeaf;
	if (!ResolveLeafNode(ch.dip, dstLeaf) || dstLeaf == nullptr) return GetOutDevPktSprayDlb(p, ch);

	uint32_t dstLeafId = dstLeaf->GetId();
	std::vector<std::pair<uint32_t, int> > candidates;
	bool hasRemoteQuality = false;
	for (int outDev : entry->second) {
		if (outDev < 0 || static_cast<uint32_t>(outDev) >= GetNDevices() || !GetDevice(outDev)->IsLinkUp()) continue;
		uint64_t qLen = (ch.udp.pg < qCnt) ? m_mmu->egress_bytes[outDev][ch.udp.pg] : 0;
		uint32_t localQ = GetQLevel(qLen);
		Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(GetDevice(outDev));
		uint32_t localLoad = dev ? GetLoadLevel(dev->calcBandwidth) : 0;
		uint32_t remoteQ = 0, remoteLoad = 0;
		uint32_t remoteQuality = GetArnPathQuality(dstLeafId, outDev, &remoteQ, &remoteLoad);
		if (remoteQuality > 0) hasRemoteQuality = true;
		uint32_t total = localQ + localLoad + remoteQuality;
		candidates.push_back(std::make_pair(total, outDev));
		if (m_arnTrace && remoteQuality > 0) {
			uint64_t traceKey = (static_cast<uint64_t>(dstLeafId) << 32) ^
				(static_cast<uint64_t>(static_cast<uint32_t>(outDev)) << 16) ^
				(static_cast<uint64_t>(remoteQ) << 8) ^ static_cast<uint64_t>(remoteLoad);
			uint32_t &traceCount = m_arnRouteTraceCount[traceKey];
			if (traceCount < 3)
				std::cout << "[ARN][glb-route] time_ns=" << Simulator::Now().GetTimeStep()
				          << " switch=" << GetId() << " dstLeaf=" << dstLeafId
				          << " nexthop=" << outDev << " local_q=" << localQ
				          << " local_load=" << localLoad << " remote_q=" << remoteQ
				          << " remote_load=" << remoteLoad << " total=" << total
				          << " sample=" << traceCount << std::endl;
			traceCount++;
		}
	}
	if (candidates.empty()) return GetOutDevPktSprayDlb(p, ch);
	if (!hasRemoteQuality) return GetOutDevPktSprayDlb(p, ch);
	std::sort(candidates.begin(), candidates.end(),
			[](const std::pair<uint32_t, int> &a, const std::pair<uint32_t, int> &b) {
				if (a.first != b.first)
					return a.first < b.first;
				return a.second < b.second;
			});
	uint32_t bestHalf = static_cast<uint32_t>((candidates.size() + 1) / 2);
	uint32_t idx = m_pktSprayRandom->GetInteger(0, bestHalf - 1);
	return candidates[idx].second;
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

bool SwitchNode::ResolveLeafNode(uint32_t ip, Ptr<Node> &leafNode) const {
	auto local = m_ipToLeafId.find(ip);
	if (local != m_ipToLeafId.end() && local->second != nullptr) { leafNode = local->second; return true; }
	auto global = g_arnIpToLeaf.find(ip);
	if (global != g_arnIpToLeaf.end() && global->second != nullptr) { leafNode = global->second; return true; }
	return false;
}

bool SwitchNode::IsSpineIngress(uint32_t inDev) const {
	auto it = m_ifToNode.find(inDev);
	return it != m_ifToNode.end() && it->second != nullptr && it->second->GetNodeType() != 0;
}

bool SwitchNode::IsSpineSwitch() const {
	if (m_isSpine) return true;
	if (m_isLeaf) return false;
	bool host = false, sw = false;
	for (const auto &entry : m_ifToNode) {
		if (!entry.second) continue;
		if (entry.second->GetNodeType() == 0) host = true; else sw = true;
	}
	return sw && !host;
}

bool SwitchNode::IsLeafSwitch() const {
	if (m_isLeaf) return true;
	if (m_isSpine) return false;
	for (const auto &entry : m_ifToNode)
		if (entry.second && entry.second->GetNodeType() == 0) return true;
	return true; // legacy topologies have no explicit role metadata
}

bool SwitchNode::ResolveArnSourceInterface(uint32_t inDev, Ptr<SwitchNode> srcSw,
										 uint32_t &srcIf) const {
	if (!srcSw) return false;

	// Same-DC congestion: the reporting spine is directly connected to srcLeaf.
	auto directIt = srcSw->m_nodeToIf.find(GetId());
	if (directIt != srcSw->m_nodeToIf.end()) {
		srcIf = directIt->second;
		return true;
	}

	// Cross-DC congestion: the reporting spine is reached through the ingress
	// neighbor, which is the source-side spine connected to srcLeaf.
	auto ingressIt = m_ifToNode.find(inDev);
	if (ingressIt == m_ifToNode.end() || ingressIt->second == nullptr) return false;
	auto upstreamIt = srcSw->m_nodeToIf.find(ingressIt->second->GetId());
	if (upstreamIt == srcSw->m_nodeToIf.end()) return false;
	srcIf = upstreamIt->second;
	return true;
}

void SwitchNode::CheckAndSendArn(uint32_t inDev, uint32_t outDev, uint32_t qIndex,
										 Ptr<Packet> p, CustomHeader &ch) {
	if (!m_arn || ch.l3Prot != 0x11 || ch.udp.fwd_mode != 1 || qIndex == 0 || p->GetSize() < 1000)
		return;
	bool spine = IsSpineSwitch();
	bool leaf = !spine && IsLeafSwitch();
	if (!spine && !leaf) return;
	if (leaf && IsSpineIngress(inDev)) return;
	Ptr<Node> srcLeaf, dstLeaf;
	if (!ResolveLeafNode(ch.sip, srcLeaf) || !ResolveLeafNode(ch.dip, dstLeaf)) return;
	uint32_t srcIf = inDev;
	if (spine) {
		Ptr<SwitchNode> srcSw = DynamicCast<SwitchNode>(srcLeaf);
		if (!ResolveArnSourceInterface(inDev, srcSw, srcIf)) {
			if (m_arnTrace)
				std::cout << "[ARN][send-skip] time_ns=" << Simulator::Now().GetTimeStep()
				          << " switch=" << GetId() << " reason=src-interface-miss"
				          << " inDev=" << inDev << " outDev=" << outDev
				          << " srcLeaf=" << srcLeaf->GetId()
				          << " dstLeaf=" << dstLeaf->GetId() << std::endl;
			return;
		}
	}
	ArnHeader::FlowKey key;
	key.src = dstLeaf->GetId(); key.dst = srcLeaf->GetId();
	key.sport = spine ? srcIf : outDev;
	key.dport = spine ? outDev : inDev;
	ArnHeader::FlowInfo info;
	info.q_len = m_mmu->egress_bytes[outDev][qIndex];
	info.q_level = GetQLevel(info.q_len);
	Ptr<QbbNetDevice> out = DynamicCast<QbbNetDevice>(GetDevice(outDev));
	info.load_level = out ? GetLoadLevel(out->calcBandwidth) : 0;
	info.ts = Simulator::Now().GetTimeStep();
	uint64_t clearThreshold = m_congestionQlen - m_congestionQlen / 8;
	uint64_t interval = static_cast<uint64_t>(m_arnInterval.GetTimeStep());
	auto event = m_arn_event.find(key);
	uint32_t previous = event == m_arn_event.end() ?
		(spine ? ArnHeader::REMOTE_CLEAR : ArnHeader::LOCAL_CLEAR) : event->second.arn_type;
	uint64_t previousTs = event == m_arn_event.end() ? 0 : event->second.ts;
	bool trigger = info.q_len > m_congestionQlen &&
		(previous == (spine ? ArnHeader::REMOTE_CLEAR : ArnHeader::LOCAL_CLEAR) ||
		 info.ts >= previousTs + interval);
	bool clear = info.q_len < clearThreshold &&
		previous == (spine ? ArnHeader::REMOTE_ARN : ArnHeader::LOCAL_ARN);
	if (!trigger && !clear) return;
	info.arn_type = trigger ? (spine ? ArnHeader::REMOTE_ARN : ArnHeader::LOCAL_ARN)
								: (spine ? ArnHeader::REMOTE_CLEAR : ArnHeader::LOCAL_CLEAR);
	m_arn_event[key] = info;
	if (m_arnTrace)
		std::cout << "[ARN][send] time_ns=" << info.ts << " switch=" << GetId()
		          << " type=" << info.arn_type << " trigger=" << trigger
		          << " clear=" << clear << " inDev=" << inDev
		          << " outDev=" << outDev << " srcIf=" << srcIf
		          << " q_len=" << info.q_len << " q_level=" << info.q_level
		          << " load_level=" << info.load_level
		          << " arn_src=" << key.src << " arn_dst=" << key.dst
		          << " arn_sport=" << key.sport << " arn_dport=" << key.dport
		          << " dstLeaf=" << key.src << " srcLeaf=" << key.dst << std::endl;
	if (spine) {
		Ptr<QbbNetDevice> in = DynamicCast<QbbNetDevice>(GetDevice(inDev));
		if (in) in->SendArn(0, key, info, ch);
	} else {
		Ptr<QbbNetDevice> in = DynamicCast<QbbNetDevice>(GetDevice(inDev));
		if (in) {
			CustomHeader arnCh = ch;
			Ptr<Packet> arnPacket = in->ArnHeaderProcess(key, info, arnCh);
			SwitchReceiveArn(in, arnPacket, arnCh, outDev);
		}
	}
}

bool SwitchNode::SwitchReceiveArn(Ptr<NetDevice>, Ptr<Packet>, CustomHeader &ch,
											uint32_t congestedPath) {
	if (!m_arn || !IsLeafSwitch() || ch.l3Prot != 0xFA) return true;
	ArnHeader::FlowInfo info;
	info.q_len = ch.arn.flowInfo.qlen;
	info.q_level = ch.arn.flowInfo.q_level;
	info.load_level = ch.arn.flowInfo.load_level;
	info.arn_type = ch.arn.flowInfo.arn_type;
	info.ts = ch.arn.flowInfo.ts;
	uint32_t dstLeaf = ch.arn.flowKey.src;
	// Match the reference ARN behavior: LOCAL_ARN is a local control event and
	// should not become a cached GLB path-quality penalty.
	if (info.arn_type != ArnHeader::LOCAL_ARN)
		std::get<0>(m_arn_receive[dstLeaf])[congestedPath] = info;
	if (info.arn_type == ArnHeader::REMOTE_ARN || info.arn_type == ArnHeader::REMOTE_PERIOD)
		std::get<1>(m_arn_receive[dstLeaf])[congestedPath] = info.ts;
	else if (info.arn_type == ArnHeader::REMOTE_CLEAR || info.arn_type == ArnHeader::LOCAL_CLEAR)
		std::get<2>(m_arn_receive[dstLeaf])[congestedPath] = info.ts;
	if (m_arnTrace)
		std::cout << "[ARN][source-leaf-read] time_ns=" << Simulator::Now().GetTimeStep()
		          << " switch=" << GetId() << " congestedPath=" << congestedPath
		          << " type=" << info.arn_type << " event_ts=" << info.ts
		          << " q_len=" << info.q_len << " q_level=" << info.q_level
		          << " load_level=" << info.load_level
		          << " arn_src=" << ch.arn.flowKey.src
		          << " arn_dst=" << ch.arn.flowKey.dst
		          << " arn_sport=" << ch.arn.flowKey.sport
		          << " arn_dport=" << ch.arn.flowKey.dport
		          << " dstLeaf=" << dstLeaf
		          << " srcLeaf=" << ch.arn.flowKey.dst << std::endl;
	return true;
}

void SwitchNode::SendToDev(Ptr<Packet>p, CustomHeader &ch){
	int idx = GetOutDev(p, ch);
	if (idx >= 0){
		NS_ASSERT_MSG(m_devices[idx]->IsLinkUp(), "The routing table look up should return link that is up");

		// determine the qIndex
		uint32_t qIndex;
		if (ch.l3Prot == 0xFF || ch.l3Prot == 0xFE || ch.l3Prot == 0xFA || (m_ackHighPrio && (ch.l3Prot == 0xFD || ch.l3Prot == 0xFC))){  // control packets use highest priority
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
				RecordDrop();
				return; // Drop
			}
			CheckAndSendPfc(inDev, qIndex);
			CheckAndSendArn(inDev, idx, qIndex, p, ch);
		}
		m_bytes[inDev][idx][qIndex] += p->GetSize();
		m_devices[idx]->SwitchSend(qIndex, p, ch);
	}else
	{
		RecordDrop();
		return; // Drop
	}
}

void SwitchNode::RecordDrop(){
	m_dropCnt++;
}

uint64_t SwitchNode::GetDropCount() const{
	return m_dropCnt;
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
	if (!node) return;
	m_ifToNode[intf_idx] = node;
	m_nodeToIf.emplace(node->GetId(), intf_idx);
}

void SwitchNode::AddInterfaceEntry(uint32_t node_id, uint32_t intf_idx) {
	m_nodeToIf[node_id] = intf_idx;
}

void SwitchNode::RegisterHostLeaf(uint32_t ip, Ptr<Node> leaf) {
	if (leaf) g_arnIpToLeaf[ip] = leaf;
}

void SwitchNode::ClearTable(){
	m_rtTable.clear();
	m_arnRouteTraceCount.clear();
}

// This function can only be called in switch mode
bool SwitchNode::SwitchReceiveFromDevice(Ptr<NetDevice> device, Ptr<Packet> packet, CustomHeader &ch){
	if (ch.l3Prot == 0xFA) {
		FlowIdTag t;
		uint32_t inDev = packet->PeekPacketTag(t) ? t.GetFlowId() : 0;
		if (IsLeafSwitch())
			return SwitchReceiveArn(device, packet, ch, inDev);
		// A remote ARN can cross another spine (notably the 500us 68/69
		// inter-DC links), so intermediate spines route it toward the source.
		SendToDev(packet, ch);
		return true;
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
