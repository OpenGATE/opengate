/* Copyright (C): OpenGATE Collaboration. See LICENSE.md for LGPL terms. */
#ifndef GateAMDMActor_lookUpTable_h
#define GateAMDMActor_lookUpTable_h

#include <map>
#include <string>
#include <vector>

// Immutable after loading. Each charge has its own energy grid and endpoints.
class GateAMDMLookUpTable {
public:
  void Read(const std::string &filename, int bins);
  bool Find(int charge, double energy, std::vector<double> &values) const;

private:
  struct Row {
    double energy;
    std::vector<double> values; // gamma bins, then delta bins
  };
  std::map<int, std::vector<Row>> fData;
};
#endif
