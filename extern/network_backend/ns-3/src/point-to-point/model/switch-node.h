#ifndef SWITCH_NODE_H
#define SWITCH_NODE_H

#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <ns3/node.h>
#include "ns3/arn-header.h"
#include "qbb-net-device.h"
#include "switch-mmu.h"
#include "pint.h"

namespace ns3 {

class Packet;

class SwitchNode : public Node{
public:
	// Forwarding strategy enums
	enum FlowStrategy { FLOW_STRATEGY_ECMP = 0 };
	enum PacketStrategy {
		PKT_STRATEGY_RR = 0
	};
	enum ArnPacketStrategy {
		ARN_PKT_STRATEGY_SCALE = 0,
		ARN_PKT_STRATEGY_REJECT = 1,
		ARN_PKT_STRATEGY_DLB = 2,
		ARN_PKT_STRATEGY_GLB = 3
	};

	static const uint32_t pCnt = 1025;	// Number of ports used
	static const uint32_t qCnt = 8;	// Number of queues/priorities used
	uint32_t m_ecmpSeed;
	std::unordered_map<uint32_t, std::vector<int> > m_rtTable; // map from ip address (u32) to possible ECMP port (index of dev)

	// monitor of PFC
	uint32_t m_bytes[pCnt][pCnt][qCnt]; // m_bytes[inDev][outDev][qidx] is the bytes from inDev enqueued for outDev at qidx
	
	uint64_t m_txBytes[pCnt]; // counter of tx bytes

	uint32_t m_lastPktSize[pCnt];
	uint64_t m_lastPktTs[pCnt]; // ns
	double m_u[pCnt];

	// Packet spray round-robin counter per ingress port
	uint32_t m_rrCounter[pCnt];

protected:
	bool m_ecnEnabled;
	uint32_t m_ccMode;
	uint64_t m_maxRtt;

	uint32_t m_ackHighPrio; // set high priority for ACK/NACK

	// Strategy configuration
	uint32_t m_flowStrategy;
	uint32_t m_packetStrategy;
	uint32_t m_arnPacketStrategy;

	// ARN congestion notification configuration.
	bool m_arn;
	bool m_isSpine;
	bool m_isLeaf;
	Time m_arnInterval;
	uint64_t m_congestionQlen;

private:
	int GetOutDev(Ptr<const Packet>, CustomHeader &ch);
	int GetOutDevFlowECMP(Ptr<const Packet>, CustomHeader &ch);
	int GetOutDevPktSprayRR(Ptr<const Packet>, CustomHeader &ch);
	int GetOutDevPktSprayArn(Ptr<const Packet>, CustomHeader &ch);
	int GetOutDevRouteArnReject(Ptr<const Packet>, CustomHeader &ch);
	int GetOutDevRouteDlb(Ptr<const Packet>, CustomHeader &ch);
	int GetOutDevRouteGlb(Ptr<const Packet>, CustomHeader &ch);
	void SendToDev(Ptr<Packet>p, CustomHeader &ch);
	static uint32_t EcmpHash(const uint8_t* key, size_t len, uint32_t seed);
	void CheckAndSendPfc(uint32_t inDev, uint32_t qIndex);
	void CheckAndSendResume(uint32_t inDev, uint32_t qIndex);
	void CheckAndSendArn(uint32_t inDev, uint32_t outDev, uint32_t qIndex, Ptr<Packet> p, CustomHeader &ch);
	void AddRejectFlowTable(CustomHeader &ch, uint32_t rejectedPort);
	void ClearRejectFlowTable(CustomHeader &ch, uint32_t rejectedPort);
	bool IsActiveArn(const ArnHeader::FlowInfo &flowInfo) const;
	uint32_t GetArnPathCost(uint32_t dstLeafId, uint32_t outDev) const;
	uint32_t GetArnPathQuality(uint32_t dstLeafId,
	                           uint32_t outDev,
	                           uint32_t *qLevel = nullptr,
	                           uint32_t *loadLevel = nullptr) const;
	uint32_t GetQLevel(uint64_t qlen) const;
	uint32_t GetLoadLevel(double load) const;
	bool ResolveLeafNode(uint32_t ip, Ptr<Node>& leafNode) const;
	bool IsSpineIngress(uint32_t inDev) const;
	bool HasHostNeighbor() const;
	bool HasSwitchNeighbor() const;
	bool IsLeafSwitch();
	bool IsSpineSwitch();

	static std::unordered_map<uint32_t, Ptr<Node> > s_ipToLeafId;
public:
	Ptr<SwitchMmu> m_mmu;
	std::unordered_map<uint32_t, Ptr<Node> > m_ipToLeafId;
	std::unordered_map<uint32_t, uint32_t> m_nodeToIf;
	std::unordered_map<uint32_t, Ptr<Node> > m_ifToNode;
	std::unordered_map<ArnHeader::FlowKey, ArnHeader::FlowInfo, ArnHeader::FlowKeyHash> m_arn_event;
	std::unordered_map<ArnHeader::FlowKey, std::unordered_set<uint32_t>, ArnHeader::FlowKeyHash> m_arn_flow;

	typedef std::unordered_map<uint32_t, ArnHeader::FlowInfo> port_table_profile;
	typedef std::unordered_map<uint32_t, uint64_t> arn_effect_ts;
	typedef std::unordered_map<uint32_t, uint64_t> arn_clear_ts;
	std::unordered_map<uint32_t, std::tuple<port_table_profile, arn_effect_ts, arn_clear_ts> > m_arn_receive;
	std::vector<uint64_t> q_level;
	std::vector<uint64_t> load_level;

	static TypeId GetTypeId (void);
	SwitchNode();
	void SetEcmpSeed(uint32_t seed);
	void AddTableEntry(Ipv4Address &dstAddr, uint32_t intf_idx);
	void AddNodeEntry(uint32_t intf_idx, Ptr<Node> node);
	void AddInterfaceEntry(uint32_t node_id, uint32_t intf_idx);
	void ClearTable();
	bool SwitchReceiveFromDevice(Ptr<NetDevice> device, Ptr<Packet> packet, CustomHeader &ch);
	bool SwitchReceiveArn(Ptr<NetDevice> device, Ptr<Packet> packet, CustomHeader &ch, uint32_t congestedPath);
	void SwitchNotifyDequeue(uint32_t ifIndex, uint32_t qIndex, Ptr<Packet> p);

	// for approximate calc in PINT
	int logres_shift(int b, int l);
	int log2apprx(int x, int b, int m, int l); // given x of at most b bits, use most significant m bits of x, calc the result in l bits
};

} /* namespace ns3 */

#endif /* SWITCH_NODE_H */
