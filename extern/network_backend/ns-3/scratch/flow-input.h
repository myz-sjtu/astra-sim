#ifndef ASTRA_SIM_FLOW_INPUT_H
#define ASTRA_SIM_FLOW_INPUT_H

#include <cmath>
#include <cstdint>
#include <limits>
#include <sstream>
#include <string>

namespace AstraSimFlowInput {

struct FlowRow {
  uint32_t src, dst, pg, dport, strategy, tag;
  uint64_t size;
  double start_time_seconds;
};

// Eight-column rows carry the actual Chakra comm_tag. Legacy seven-column
// rows retain their historical one-based row-number tag.
inline bool ParseFlowRow(const std::string &line, uint32_t legacy_tag,
                         FlowRow &row) {
  std::istringstream input(line.substr(0, line.find('#')));
  if (!(input >> row.src >> row.dst >> row.pg >> row.dport >> row.size >>
        row.start_time_seconds >> row.strategy)) {
    return false;
  }
  if (!std::isfinite(row.start_time_seconds) || row.start_time_seconds < 0 ||
      row.start_time_seconds >=
          static_cast<double>(std::numeric_limits<uint64_t>::max()) / 1e9 ||
      row.strategy > 1) {
    return false;
  }
  row.tag = legacy_tag;
  input >> std::ws;
  if (!input.eof()) {
    uint64_t tag;
    if (!(input >> tag) || tag > std::numeric_limits<uint32_t>::max()) {
      return false;
    }
    row.tag = static_cast<uint32_t>(tag);
    input >> std::ws;
    if (!input.eof()) {
      return false;
    }
  }
  return true;
}

inline bool IsCommentOrEmpty(const std::string &line) {
  const auto first = line.find_first_not_of(" \t\r\n");
  return first == std::string::npos || line[first] == '#';
}

} // namespace AstraSimFlowInput

#endif // ASTRA_SIM_FLOW_INPUT_H
