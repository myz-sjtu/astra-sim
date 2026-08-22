#ifndef SWITCH_NODE_H
#define SWITCH_NODE_H

#include <unordered_map>
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
	enum PacketStrategy { PKT_STRATEGY_RR = 0, PKT_STRATEGY_RANDOM = 1 };

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

private:
	int GetOutDev(Ptr<const Packet>, CustomHeader &ch);
	int GetOutDevFlowECMP(Ptr<const Packet>, CustomHeader &ch);
	int GetOutDevPathPinning(Ptr<const Packet>, CustomHeader &ch);
	int GetOutDevPktSprayRR(Ptr<const Packet>, CustomHeader &ch);
	int GetOutDevPktSprayRandom(Ptr<const Packet>, CustomHeader &ch);
	int GetInDev(Ptr<const Packet> p);
	void SendToDev(Ptr<Packet>p, CustomHeader &ch);
	static uint32_t EcmpHash(const uint8_t* key, size_t len, uint32_t seed);
	void CheckAndSendPfc(uint32_t inDev, uint32_t qIndex);
	void CheckAndSendResume(uint32_t inDev, uint32_t qIndex);
public:
	Ptr<SwitchMmu> m_mmu;

	static TypeId GetTypeId (void);
	SwitchNode();
	void SetEcmpSeed(uint32_t seed);
	void AddTableEntry(Ipv4Address &dstAddr, uint32_t intf_idx);
	void ClearTable();
	void RecordDrop();
	uint64_t GetDropCount() const;
	bool SwitchReceiveFromDevice(Ptr<NetDevice> device, Ptr<Packet> packet, CustomHeader &ch);
	void SwitchNotifyDequeue(uint32_t ifIndex, uint32_t qIndex, Ptr<Packet> p);

	// for approximate calc in PINT
	int logres_shift(int b, int l);
	int log2apprx(int x, int b, int m, int l); // given x of at most b bits, use most significant m bits of x, calc the result in l bits
};

} /* namespace ns3 */

#endif /* SWITCH_NODE_H */
