/* Copyright (C): OpenGATE Collaboration. See LICENSE.md for LGPL terms. */
#include "GateAMDMActor_lookUpTable.hh"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <limits>
#include <sstream>
#include <stdexcept>

void GateAMDMLookUpTable::Read(const std::string &filename, int bins) {
  if (bins <= 0 || bins > (std::numeric_limits<int>::max() - 2) / 2)
    throw std::invalid_argument("AMDM_Bins must be a positive integer");
  std::ifstream input(filename);
  if (!input)
    throw std::invalid_argument("AMDM cannot open LUT: " + filename);
  std::map<int, std::vector<Row>> data;
  std::string line;
  int previousCharge = 0;
  size_t lineNumber = 0;
  while (std::getline(input, line)) {
    ++lineNumber;
    line = line.substr(0, line.find('#'));
    std::istringstream stream(line);
    std::vector<double> columns;
    std::string token;
    auto fail = [&](const std::string &reason) {
      throw std::invalid_argument("AMDM LUT " + filename + ":" +
                                  std::to_string(lineNumber) + ": " + reason);
    };
    while (stream >> token) {
      try {
        size_t used;
        double value = std::stod(token, &used);
        if (used != token.size() || !std::isfinite(value))
          fail("entries must be finite numeric values");
        columns.push_back(value);
      } catch (const std::exception &) {
        fail("entries must be finite numeric values");
      }
    }
    if (columns.empty())
      continue;
    if (columns.size() != static_cast<size_t>(2 + 2 * bins))
      fail("column count must equal 2 + 2 * AMDM_Bins");
    double key = columns[0];
    if (key <= 0 || key > std::numeric_limits<int>::max() ||
        std::floor(key) != key)
      fail("charge must be a positive integer");
    int charge = static_cast<int>(key);
    if (charge < previousCharge)
      fail("charge groups must be increasing");
    if (columns[1] <= 0)
      fail("energy keys must be positive (MeV/n)");
    auto &group = data[charge];
    if (!group.empty() && columns[1] <= group.back().energy)
      fail(
          "energy keys must be unique and strictly increasing within a charge");
    group.push_back({columns[1], {columns.begin() + 2, columns.end()}});
    previousCharge = charge;
  }
  if (input.bad())
    throw std::invalid_argument("AMDM error reading LUT: " + filename);
  if (data.empty())
    throw std::invalid_argument("AMDM LUT contains no data: " + filename);
  fData = std::move(data);
}

bool GateAMDMLookUpTable::Find(int charge, double energy,
                               std::vector<double> &values) const {
  values.clear();
  auto found = fData.find(charge);
  if (found == fData.end() || std::isnan(energy))
    return false;
  const auto &rows = found->second;
  // Clamp before inspecting a lower_bound iterator, including the final charge.
  if (energy <= rows.front().energy) {
    values = rows.front().values;
  } else if (energy >= rows.back().energy) {
    values = rows.back().values;
  } else {
    auto upper = std::lower_bound(
        rows.begin(), rows.end(), energy,
        [](const Row &row, double value) { return row.energy < value; });
    if (upper->energy == energy) {
      values = upper->values;
    } else {
      const auto &lower = *std::prev(upper);
      const double fraction =
          (energy - lower.energy) / (upper->energy - lower.energy);
      values.resize(lower.values.size());
      for (size_t b = 0; b < values.size(); ++b)
        values[b] =
            lower.values[b] + fraction * (upper->values[b] - lower.values[b]);
    }
  }
  return true;
}
