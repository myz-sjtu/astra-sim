#ifndef SWITCH_MMU_H
#define SWITCH_MMU_H

#include <unordered_map>
#include <ns3/node.h>

namespace ns3 {

class Packet;

class SwitchMmu: public Object{
public:
	static const uint32_t pCnt = 1025;	// Number of ports used
	static const uint32_t qCnt = 8;	// Number of queues/priorities used
	enum PortDistanceClass {
		PORT_DISTANCE_SHORT = 0,
		PORT_DISTANCE_LONG = 1
	};

	static TypeId GetTypeId (void);

	SwitchMmu(void);

	bool CheckIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);
	bool CheckEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);
	void UpdateIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);
	void UpdateEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);
	void RemoveFromIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);
	void RemoveFromEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);

	bool CheckShouldPause(uint32_t port, uint32_t qIndex);
	bool CheckShouldResume(uint32_t port, uint32_t qIndex);
	void SetPause(uint32_t port, uint32_t qIndex);
	void SetResume(uint32_t port, uint32_t qIndex);
	//void GetPauseClasses(uint32_t port, uint32_t qIndex);
	//bool GetResumeClasses(uint32_t port, uint32_t qIndex);

	uint64_t GetPfcThreshold(uint32_t port);
	uint64_t GetSharedUsed(uint32_t port, uint32_t qIndex);

	bool ShouldSendCN(uint32_t ifindex, uint32_t qIndex);

	void ConfigEcn(uint32_t port, uint32_t _kmin, uint32_t _kmax, double _pmax);
	void ConfigHdrm(uint32_t port, uint64_t size);
	void ConfigRsrv(uint32_t port, uint64_t size);
	void ConfigPortDistance(uint32_t port, bool is_long_distance);
	bool IsLongDistancePort(uint32_t port) const;
	bool IsShortDistancePort(uint32_t port) const;
	bool HasLongDistancePort(uint32_t n_port) const;
	void ConfigDelayPort(uint32_t port);
	bool IsDelayPort(uint32_t port) const;
	void ConfigNPort(uint32_t n_port);
	void ConfigBufferSize(uint64_t size);

	// config
	uint32_t node_id;
	uint64_t buffer_size;
	uint32_t pfc_a_shift[pCnt];
	uint64_t reserve[pCnt];
	uint64_t headroom[pCnt];
	PortDistanceClass port_distance[pCnt];
	bool delay_port[pCnt];
	uint32_t resume_offset;
	uint32_t kmin[pCnt], kmax[pCnt];
	double pmax[pCnt];
	uint64_t total_hdrm;
	uint64_t total_rsrv;

	// runtime
	uint64_t shared_used_bytes;
	uint32_t hdrm_bytes[pCnt][qCnt];
	uint32_t ingress_bytes[pCnt][qCnt];
	uint32_t paused[pCnt][qCnt];
	uint32_t egress_bytes[pCnt][qCnt];
};

} /* namespace ns3 */

#endif /* SWITCH_MMU_H */
