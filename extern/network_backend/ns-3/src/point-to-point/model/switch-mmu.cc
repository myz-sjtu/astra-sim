#include <iostream>
#include <fstream>
#include "ns3/double.h"
#include "ns3/packet.h"
#include "ns3/simulator.h"
#include "ns3/object-vector.h"
#include "ns3/uinteger.h"
#include "ns3/log.h"
#include "ns3/assert.h"
#include "ns3/global-value.h"
#include "ns3/boolean.h"
#include "ns3/simulator.h"
#include "ns3/random-variable-stream.h"
#include <cstdio>
#include "switch-mmu.h"

// Headroom overflow is recorded by the caller's drop statistics. Runtime
// gating avoids one stdout line per dropped packet during batch runs.
#define printf(...) do { if (m_verboseOutput) std::printf(__VA_ARGS__); } while (0)

NS_LOG_COMPONENT_DEFINE("SwitchMmu");
namespace ns3 {
	TypeId SwitchMmu::GetTypeId(void){
		static TypeId tid = TypeId("ns3::SwitchMmu")
			.SetParent<Object>()
			.AddConstructor<SwitchMmu>()
			.AddAttribute("VerboseOutput",
				"Enable verbose MMU drop diagnostics.",
				BooleanValue(false),
				MakeBooleanAccessor(&SwitchMmu::m_verboseOutput),
				MakeBooleanChecker());
		return tid;
	}

	SwitchMmu::SwitchMmu(void){
		m_verboseOutput = false;
		buffer_size = 12 * 1024 * 1024;
		resume_offset = 3 * 1024;

		// headroom
		shared_used_bytes = 0;
		for (uint32_t i = 0; i < pCnt; i++){
			reserve[i] = 4 * 1024;
			headroom[i] = 0;
			port_distance[i] = PORT_DISTANCE_SHORT;
			delay_port[i] = false;
		}
		memset(hdrm_bytes, 0, sizeof(hdrm_bytes));
		memset(ingress_bytes, 0, sizeof(ingress_bytes));
		memset(paused, 0, sizeof(paused));
		memset(egress_bytes, 0, sizeof(egress_bytes));
	}
	bool SwitchMmu::CheckIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize){
		if (IsDelayPort(port) == true)
		{
			if (psize + hdrm_bytes[port][qIndex] > headroom[port]){
				printf("%lu %u Drop: queue:%u,%u: Headroom full\n", Simulator::Now().GetTimeStep(), node_id, port, qIndex);
				for (uint32_t i = 1; i < 64; i++)
					printf("(%u,%u)", hdrm_bytes[i][3], ingress_bytes[i][3]);
				printf("\n");
				return false;
			}
			return true;
		}
		else{
			if (psize + hdrm_bytes[port][qIndex] > headroom[port] && psize + GetSharedUsed(port, qIndex) > GetPfcThreshold(port)){
			printf("%lu %u Drop: queue:%u,%u: Headroom full\n", Simulator::Now().GetTimeStep(), node_id, port, qIndex);
			for (uint32_t i = 1; i < 64; i++)
				printf("(%u,%u)", hdrm_bytes[i][3], ingress_bytes[i][3]);
			printf("\n");
			return false;
		}
		return true;
		}
	}
	bool SwitchMmu::CheckEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize){
		return true;
	}
	void SwitchMmu::UpdateIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize){
		uint64_t new_bytes = ingress_bytes[port][qIndex] + psize;
		if (new_bytes <= reserve[port]){
			ingress_bytes[port][qIndex] += psize;
		}else {
			if (IsDelayPort(port) == false){
				uint64_t thresh = GetPfcThreshold(port);
				if (new_bytes - reserve[port] > thresh){
					hdrm_bytes[port][qIndex] += psize;
				}else {
					ingress_bytes[port][qIndex] += psize;
					shared_used_bytes += std::min<uint64_t>(psize, new_bytes - reserve[port]);
				}
			}
			else{
				hdrm_bytes[port][qIndex] += psize;
			}
		}
	}
	void SwitchMmu::UpdateEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize){
		egress_bytes[port][qIndex] += psize;
	}
	void SwitchMmu::RemoveFromIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize){
		uint32_t from_hdrm = std::min(hdrm_bytes[port][qIndex], psize);
		uint64_t from_shared = std::min<uint64_t>(
			psize - from_hdrm,
			ingress_bytes[port][qIndex] > reserve[port] ? ingress_bytes[port][qIndex] - reserve[port] : 0);
		hdrm_bytes[port][qIndex] -= from_hdrm;
		ingress_bytes[port][qIndex] -= psize - from_hdrm;
		shared_used_bytes -= from_shared;
	}
	void SwitchMmu::RemoveFromEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize){
		egress_bytes[port][qIndex] -= psize;
	}
	bool SwitchMmu::CheckShouldPause(uint32_t port, uint32_t qIndex){
		if (IsDelayPort(port) == true)
		{
			return !paused[port][qIndex] && (hdrm_bytes[port][qIndex] > resume_offset);
		}
		return !paused[port][qIndex] && (hdrm_bytes[port][qIndex] > 0 || GetSharedUsed(port, qIndex) >= GetPfcThreshold(port));
	}
	bool SwitchMmu::CheckShouldResume(uint32_t port, uint32_t qIndex){
		if (!paused[port][qIndex])
			return false;
		if (IsDelayPort(port) == true){
			return hdrm_bytes[port][qIndex] == 0;
		}
		uint64_t shared_used = GetSharedUsed(port, qIndex);
		return hdrm_bytes[port][qIndex] == 0 && (shared_used == 0 || shared_used + resume_offset <= GetPfcThreshold(port));
	}
	void SwitchMmu::SetPause(uint32_t port, uint32_t qIndex){
		paused[port][qIndex] = true;
	}
	void SwitchMmu::SetResume(uint32_t port, uint32_t qIndex){
		paused[port][qIndex] = false;
	}

	uint64_t SwitchMmu::GetPfcThreshold(uint32_t port){
		uint64_t reserved_bytes = total_hdrm + total_rsrv + shared_used_bytes;
		if (reserved_bytes >= buffer_size)
			return 0;
		return (buffer_size - reserved_bytes) >> pfc_a_shift[port];
	}
	uint64_t SwitchMmu::GetSharedUsed(uint32_t port, uint32_t qIndex){
		uint32_t used = ingress_bytes[port][qIndex];
		return used > reserve[port] ? used - reserve[port] : 0;
	}
	bool SwitchMmu::ShouldSendCN(uint32_t ifindex, uint32_t qIndex){
		if (qIndex == 0)
			return false;
		if (egress_bytes[ifindex][qIndex] > kmax[ifindex])
			return true;
		if (egress_bytes[ifindex][qIndex] > kmin[ifindex]){
			double p = pmax[ifindex] * double(egress_bytes[ifindex][qIndex] - kmin[ifindex]) / (kmax[ifindex] - kmin[ifindex]);
			Ptr<UniformRandomVariable> rng_generator = CreateObject<UniformRandomVariable> ();
			rng_generator->SetAttribute ("Min", DoubleValue (0));
			rng_generator->SetAttribute ("Max", DoubleValue (1));
			if (rng_generator->GetValue() < p)
				return true;
		}
		return false;
	}
	void SwitchMmu::ConfigEcn(uint32_t port, uint32_t _kmin, uint32_t _kmax, double _pmax){
		kmin[port] = _kmin * 1000;
		kmax[port] = _kmax * 1000;
		pmax[port] = _pmax;
	}
	void SwitchMmu::ConfigHdrm(uint32_t port, uint64_t size){
		headroom[port] = size;
	}
	void SwitchMmu::ConfigRsrv(uint32_t port, uint64_t size){
		reserve[port] = size;
	}
	void SwitchMmu::ConfigPortDistance(uint32_t port, bool is_long_distance){
		NS_ASSERT_MSG(port < pCnt, "MMU port index is out of range");
		port_distance[port] = is_long_distance ? PORT_DISTANCE_LONG : PORT_DISTANCE_SHORT;
	}
	bool SwitchMmu::IsLongDistancePort(uint32_t port) const{
		NS_ASSERT_MSG(port < pCnt, "MMU port index is out of range");
		return port_distance[port] == PORT_DISTANCE_LONG;
	}
	bool SwitchMmu::IsShortDistancePort(uint32_t port) const{
		NS_ASSERT_MSG(port < pCnt, "MMU port index is out of range");
		return port_distance[port] == PORT_DISTANCE_SHORT;
	}
	bool SwitchMmu::HasLongDistancePort(uint32_t n_port) const{
		NS_ASSERT_MSG(n_port < pCnt, "MMU port count is out of range");
		for (uint32_t i = 1; i <= n_port; i++){
			if (IsLongDistancePort(i))
				return true;
		}
		return false;
	}
	void SwitchMmu::ConfigDelayPort(uint32_t port){
		NS_ASSERT_MSG(port < pCnt, "MMU port index is out of range");
		delay_port[port] = true;
	}
	bool SwitchMmu::IsDelayPort(uint32_t port) const{
		NS_ASSERT_MSG(port < pCnt, "MMU port index is out of range");
		return delay_port[port];
	}
	void SwitchMmu::ConfigNPort(uint32_t n_port){
		total_hdrm = 0;
		total_rsrv = 0;
		for (uint32_t i = 1; i <= n_port; i++){
			total_hdrm += headroom[i];
			total_rsrv += reserve[i];
		}
	}
	void SwitchMmu::ConfigBufferSize(uint64_t size){
		buffer_size = size;
	}
}
