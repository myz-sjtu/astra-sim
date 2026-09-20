#ifndef SWITCH_NODE_H
#define SWITCH_NODE_H

#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <ns3/arn-header.h>
#include <ns3/custom-header.h>
#include <ns3/node.h>
#include <ns3/random-variable-stream.h>
#include "qbb-net-device.h"
#include "switch-mmu.h"
#include "pint.h"

namespace ns3 {

class Packet;

class SwitchNode : public Node{
public:
	// Forwarding strategy enums
	enum FlowStrategy { FLOW_STRATEGY_ECMP = 0, FLOW_STRATEGY_PATH_PINNING = 1 };
	enum PacketStrategy { PKT_STRATEGY_RR = 0, PKT_STRATEGY_RANDOM = 1, PKT_STRATEGY_DLB = 2 };
	enum ArnPacketStrategy { ARN_PKT_STRATEGY_GLB = 3 };

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
	Ptr<UniformRandomVariable> m_pktSprayRandom;

	uint64_t m_dropCnt;

protected:
	bool m_ecnEnabled;
	uint32_t m_ccMode;
	uint64_t m_maxRtt;

	uint32_t m_ackHighPrio; // set high priority for ACK/NACK

	// Strategy configuration
	uint32_t m_flowStrategy;
	uint32_t m_packetStrategy;
	uint32_t m_arnPacketStrategy;
	bool m_arn;
	bool m_isSpine;
	bool m_isLeaf;
	Time m_arnInterval;
	uint64_t m_congestionQlen;
	bool m_arnTrace;

private:
	int GetOutDev(Ptr<const Packet>, CustomHeader &ch);
	int GetOutDevFlowECMP(Ptr<const Packet>, CustomHeader &ch);
	int GetOutDevPathPinning(Ptr<const Packet>, CustomHeader &ch);
	int GetOutDevPktSprayRR(Ptr<const Packet>, CustomHeader &ch);
	int GetOutDevPktSprayRandom(Ptr<const Packet>, CustomHeader &ch);
	int GetOutDevPktSprayDlb(Ptr<const Packet>, CustomHeader &ch);
	int GetOutDevRouteGlb(Ptr<const Packet>, CustomHeader &ch);
	int GetInDev(Ptr<const Packet> p);
	void SendToDev(Ptr<Packet>p, CustomHeader &ch);
	static uint32_t EcmpHash(const uint8_t* key, size_t len, uint32_t seed);
	void CheckAndSendPfc(uint32_t inDev, uint32_t qIndex);
	void CheckAndSendResume(uint32_t inDev, uint32_t qIndex);
	void CheckAndSendArn(uint32_t inDev, uint32_t outDev, uint32_t qIndex, Ptr<Packet> p, CustomHeader &ch);
	uint32_t GetQLevel(uint64_t qlen) const;
	uint32_t GetLoadLevel(double load) const;
	uint32_t GetArnPathQuality(uint32_t dstLeafId, uint32_t outDev,
	                           uint32_t *qLevel = nullptr,
	                           uint32_t *loadLevel = nullptr) const;
	bool ResolveArnSourceInterface(uint32_t inDev, Ptr<SwitchNode> srcSw, uint32_t &srcIf) const;
	bool ResolveLeafNode(uint32_t ip, Ptr<Node> &leafNode) const;
	bool IsSpineIngress(uint32_t inDev) const;
	bool IsLeafSwitch() const;
	bool IsSpineSwitch() const;
public:
	Ptr<SwitchMmu> m_mmu;

	static TypeId GetTypeId (void);
	SwitchNode();
	void SetEcmpSeed(uint32_t seed);
	void AddTableEntry(Ipv4Address &dstAddr, uint32_t intf_idx);
	void AddNodeEntry(uint32_t intf_idx, Ptr<Node> node);
	void AddInterfaceEntry(uint32_t node_id, uint32_t intf_idx);
	static void RegisterHostLeaf(uint32_t ip, Ptr<Node> leaf);
	void ClearTable();
	void RecordDrop();
	uint64_t GetDropCount() const;
	bool SwitchReceiveFromDevice(Ptr<NetDevice> device, Ptr<Packet> packet, CustomHeader &ch);
	bool SwitchReceiveArn(Ptr<NetDevice> device, Ptr<Packet> packet, CustomHeader &ch, uint32_t congestedPath);
	void SwitchNotifyDequeue(uint32_t ifIndex, uint32_t qIndex, Ptr<Packet> p);

	std::unordered_map<uint32_t, Ptr<Node> > m_ipToLeafId;
	std::unordered_map<uint32_t, uint32_t> m_nodeToIf;
	std::unordered_map<uint32_t, Ptr<Node> > m_ifToNode;
	std::unordered_map<ArnHeader::FlowKey, ArnHeader::FlowInfo, ArnHeader::FlowKeyHash> m_arn_event;
	typedef std::unordered_map<uint32_t, ArnHeader::FlowInfo> ArnProfile;
	typedef std::unordered_map<uint32_t, uint64_t> ArnTimestampMap;
	std::unordered_map<uint32_t, std::tuple<ArnProfile, ArnTimestampMap, ArnTimestampMap> > m_arn_receive;
	std::unordered_map<uint64_t, uint32_t> m_arnRouteTraceCount;
	std::vector<uint64_t> q_level;
	std::vector<uint64_t> load_level;

	// for approximate calc in PINT
	int logres_shift(int b, int l);
	int log2apprx(int x, int b, int m, int l); // given x of at most b bits, use most significant m bits of x, calc the result in l bits
};

} /* namespace ns3 */

#endif /* SWITCH_NODE_H */
