#!/usr/bin/env python3
"""Dependency-free regression checks; compile production C++ with small ns-3 stubs.

Run: python3 tests/packet_regressions/test_packet_fixes.py
Requires a C++17 compiler (CXX, c++, or g++). Does not launch a simulation.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
from typing import Any
import unittest

ROOT = Path(__file__).resolve().parents[2]
NS3 = ROOT / 'extern/network_backend/ns-3'


def production_function(text: str, signature: str) -> str:
    start = text.index(signature)
    opening = text.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


class PacketFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='packet-regressions-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.directory = Path(cls.temp.name)
        compiler = shlex.split(os.environ.get('CXX', 'c++'))
        if not shutil.which(compiler[0]):
            raise RuntimeError('C++17 compiler required; set CXX')
        rdma = (NS3 / 'src/point-to-point/model/rdma-hw.cc').read_text()
        function = production_function(rdma, 'int RdmaHw::ReceiverCheckSeq(')
        # Use the actual SetupNetwork flow-loading block, including key lookup,
        # duplicate detection, and seconds-to-nanoseconds conversion.
        common = (NS3 / 'scratch/common.h').read_text()
        start = common.index('  configured_flow_start_ns.clear();')
        end = common.index('  std::vector<uint32_t> node_type', start)
        flow_loading = common[start:end]
        harness = r'''
#include "flow-input.h"
#include <cassert>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <tuple>
#include <unordered_map>
using namespace std;
template<class T> using Ptr = shared_ptr<T>;
struct Simulator { static uint64_t Now() { return 100; } };
uint64_t MicroSeconds(double n) { return static_cast<uint64_t>(n * 1000); }
struct RdmaRxQueuePair {
  uint32_t ReceiverNextExpectedSeq = 0, m_milestone_rx = 1, m_lastNACK = 0;
  bool m_oooEnabled = true;
  uint64_t m_nackTimer = 0;
  unordered_map<uint32_t, uint32_t> m_oooReceived;
};
struct RdmaHw {
  uint32_t m_ack_interval = 1, m_chunk = 4000;
  double m_nack_interval = 1;
  bool m_backto0 = false;
  int ReceiverCheckSeq(uint32_t, Ptr<RdmaRxQueuePair>, uint32_t);
};
'''
        harness += function
        harness += r'''
map<tuple<uint32_t,uint32_t,uint32_t>, uint64_t> configured_flow_start_ns;
map<tuple<uint32_t,uint32_t,uint32_t>, uint8_t> configured_flow_fwd_mode;
bool LoadFlows(const char* filename) {
  ifstream flowf(filename);
  uint32_t flow_num;
  if (!(flowf >> flow_num)) return false;
'''
        harness += flow_loading
        harness += r'''
  return true;
}
int main(int argc, char** argv) {
  if (argc == 2) {
    if (!LoadFlows(argv[1])) return 2;
    for (const auto &item : configured_flow_start_ns) {
      cout << get<0>(item.first) << " " << get<1>(item.first) << " "
           << get<2>(item.first) << " " << item.second << " "
           << unsigned(configured_flow_fwd_mode.at(item.first)) << "\n";
    }
    return 0;
  }
  RdmaHw hw;
  auto q = make_shared<RdmaRxQueuePair>();
  hw.ReceiverCheckSeq(1000, q, 500); // short final packet arrives first
  assert(q->ReceiverNextExpectedSeq == 0 && q->m_oooReceived.size() == 1);
  hw.ReceiverCheckSeq(0, q, 1000);
  assert(q->ReceiverNextExpectedSeq == 1500 && q->m_oooReceived.empty());
  assert(hw.ReceiverCheckSeq(1000, q, 500) == 3); // duplicate
  assert(q->m_oooReceived.empty());
  q = make_shared<RdmaRxQueuePair>();
  hw.ReceiverCheckSeq(2000, q, 300);
  hw.ReceiverCheckSeq(1000, q, 1000);
  assert(hw.ReceiverCheckSeq(1000, q, 1000) == 3); // cached duplicate
  hw.ReceiverCheckSeq(0, q, 1000);
  assert(q->ReceiverNextExpectedSeq == 2300 && q->m_oooReceived.empty());
  q = make_shared<RdmaRxQueuePair>();
  q->m_oooEnabled = false;
  assert(hw.ReceiverCheckSeq(1000, q, 500) == 2); // in-order path still NACKs
  hw.ReceiverCheckSeq(0, q, 1000);
  hw.ReceiverCheckSeq(1000, q, 500);
  assert(q->ReceiverNextExpectedSeq == 1500);
}
'''
        source = cls.directory / 'regression.cc'
        source.write_text(harness)
        cls.binary = cls.directory / 'regression'
        subprocess.run(compiler + ['-std=c++17', '-Wall', '-Wextra', '-Werror',
                                  '-I', str(NS3 / 'scratch'), str(source),
                                  '-o', str(cls.binary)], check=True)

    def load_rows(self, rows):
        path = self.directory / 'flows.txt'
        path.write_text(rows)
        return subprocess.run([str(self.binary), str(path)], capture_output=True, text=True)

    def test_short_tail_reordering_and_duplicates(self):
        subprocess.run([str(self.binary)], check=True)

    def test_custom_tags_and_legacy_rows(self):
        result = self.load_rows('3\n# comment\n\n'
                                '0 1 3 100 1500 2.000000123 1 42\n'
                                '0 1 3 100 500 3 0 1001 # phase tag\n'
                                '1 0 3 100 1000 4 1\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            '0 1 42 2000000123 1', '0 1 1001 3000000000 0',
            '1 0 3 4000000000 1'])

    def test_invalid_and_duplicate_rows_fail(self):
        bad_inputs = [
            '1\n0 1 3 100 1500 2 1 not-a-tag\n',
            '1\n0 1 3 100 1500 2 1 4294967296\n',
            '1\n0 1 3 100 1500 2 1 42 extra\n',
            '1\n0 1 3 100 1500 -2 1 42\n',
            '1\n0 1 3 100 1500 2 3 42\n',
            '2\n0 1 3 100 1500 2 1 42\n0 1 3 100 500 3 0 42\n',
            '2\n0 1 3 100 1500 2 1\n',
        ]
        for contents in bad_inputs:
            with self.subTest(contents=contents):
                self.assertNotEqual(self.load_rows(contents).returncode, 0)

    def test_generator_roundtrip_with_nonsequential_tags(self):
        # Load the real writer without importing Chakra/protobuf, which it does
        # not need. All generated rows are then consumed by production C++.
        tree = ast.parse((ROOT / 'examples/custom_network/generate_custom_inputs.py').read_text())
        functions = [node for node in tree.body
                     if (isinstance(node, ast.FunctionDef) and node.name in
                         ('format_seconds_from_ns', 'write_flow_file'))
                     or (isinstance(node, ast.Assign) and any(
                         isinstance(target, ast.Name) and target.id == 'NS_PER_SECOND'
                         for target in node.targets))]
        namespace = {'Path': Path, 'Any': Any}
        exec(compile(ast.Module(body=functions, type_ignores=[]), 'generate_custom_inputs.py', 'exec'), namespace)
        path = self.directory / 'generated-flow.txt'
        namespace['write_flow_file']({'flows': [
            {'src': 0, 'dst': 1, 'bytes': 1500, 'start_time_ns': 2000000123,
             'fwd_mode': 1, 'tag': 42},
            {'src': 0, 'dst': 1, 'bytes': 500, 'start_time_ns': 3000000000,
             'fwd_mode': 0, 'tag': 1001},
        ]}, path)
        result = subprocess.run([str(self.binary), str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            '0 1 42 2000000123 1', '0 1 1001 3000000000 0'])

    def test_base_arn_thresholds_are_scalars(self):
        for case in (1, 2, 3):
            path = ROOT / f'examples/custom_network/config_case{case}.txt'
            values = [line.split() for line in path.read_text().splitlines()
                      if line.startswith('ARN_CONGESTION_QLEN ')]
            self.assertEqual(values, [['ARN_CONGESTION_QLEN', '300000']])


if __name__ == '__main__':
    unittest.main(verbosity=2)
