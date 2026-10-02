/* Copyright (C): OpenGATE Collaboration. See LICENSE.md for LGPL terms. */
#ifndef GateAMDMActor_lookUpTable_h
#define GateAMDMActor_lookUpTable_h

#include <map>
#include <string>
#include <vector>

/** Immutable during scoring; each charge owns its energy grid and endpoints. */
class GateAMDMLookUpTable {
public:
  /** Load a whitespace/comment table with 2 + 2*bins finite columns per row.
   * Validate positive keys and ordered unique energy grids. Raise
   * std::invalid_argument on malformed/unreadable input and retain old data.
   */
  void Read(const std::string &filename, int bins);
  /** Fill values with gamma bins followed by delta bins at energy in MeV/n.
   * Interpolate linearly within a group and clamp at its endpoints. Return
   * false and clear values for a missing charge or NaN energy; infinities
   * clamp.
   */
  bool Find(int charge, double energy, std::vector<double> &values) const;

private:
  struct Row {
    double energy;
    std::vector<double> values; // gamma bins, then delta bins
  };
  std::map<int, std::vector<Row>> fData;
};
#endif
