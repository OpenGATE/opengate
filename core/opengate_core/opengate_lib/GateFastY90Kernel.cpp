/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateFastY90Kernel.h"
#include <algorithm>
#include <cmath>
#include <iterator>
#include <numeric>
#include <stdexcept>

namespace {
template <size_t N>
void MakeCDF(const double (&weights)[N], std::array<double, N> &cdf) {
  std::partial_sum(std::begin(weights), std::end(weights), cdf.begin());
  const auto total = cdf.back();
  for (auto &value : cdf)
    value /= total;
  cdf.back() = 1;
}

template <typename Container>
size_t FindBin(const Container &cdf, double probability) {
  // upper_bound also skips empty bins when probability is exactly zero.
  const auto end = std::end(cdf);
  const auto found = std::upper_bound(std::begin(cdf), end, probability);
  return std::distance(std::begin(cdf), found == end ? end - 1 : found);
}

size_t ConditionalEnergyBin(double energy) {
  return std::min(static_cast<size_t>(energy / 0.02), size_t{99});
}
} // namespace

GateFastY90Kernel::GateFastY90Kernel(double minBremEnergy,
                                     double positronProbability)
    : fPositronProbability(positronProbability) {
  if (!std::isfinite(minBremEnergy) || minBremEnergy < 0 || minBremEnergy >= 2)
    throw std::invalid_argument("FastY90Source min_brem_energy must be finite "
                                "and in [0, 2 MeV).");
  if (!std::isfinite(positronProbability) || positronProbability < 0 ||
      positronProbability > 1)
    throw std::invalid_argument("FastY90Source positron_probability must be "
                                "finite and in [0, 1].");

  // GATE 9 rounds the cutoff down to a 10 keV bin boundary.
  fFirstEnergyBin = static_cast<int>(minBremEnergy / 0.01);
  std::partial_sum(std::begin(mEnergyTable) + fFirstEnergyBin,
                   std::end(mEnergyTable),
                   fEnergyCDF.begin() + fFirstEnergyBin);
  fBremsstrahlungYield = fEnergyCDF.back();
  if (GetTotalYield() <= 0)
    throw std::invalid_argument("FastY90Source has zero emission yield.");
  if (fBremsstrahlungYield > 0) {
    for (auto &value : fEnergyCDF)
      value /= fBremsstrahlungYield;
    fEnergyCDF.back() = 1;
  }
}

GateFastY90Kernel::ConditionalCDFs::ConditionalCDFs() {
  for (size_t i = 0; i < range.size(); ++i) {
    MakeCDF(mRangeTable[i], range[i]);
    MakeCDF(mAngleTable[i], angle[i]);
  }
}

const GateFastY90Kernel::ConditionalCDFs &
GateFastY90Kernel::GetConditionalCDFs() {
  // Shared immutable tables; C++ guarantees thread-safe initialization.
  static const ConditionalCDFs cdfs;
  return cdfs;
}

bool GateFastY90Kernel::IsPositron(double probability) const {
  return probability < fPositronProbability / GetTotalYield();
}

double GateFastY90Kernel::SampleBremsstrahlungEnergy(double probability,
                                                     double binFraction) const {
  return (FindBin(fEnergyCDF, probability) + binFraction) * 0.01;
}

double GateFastY90Kernel::SamplePositronEnergy(double probability) const {
  // The positron table is already a CDF and GATE 9 samples integer keV.
  const auto found =
      std::lower_bound(std::begin(mPositronEnergyTable),
                       std::end(mPositronEnergyTable), probability);
  return std::distance(std::begin(mPositronEnergyTable), found) * 0.001;
}

double GateFastY90Kernel::SampleRange(double energy, double probability,
                                      double binFraction) const {
  const auto &cdf = GetConditionalCDFs().range[ConditionalEnergyBin(energy)];
  return (FindBin(cdf, probability) + binFraction) * 0.1;
}

double GateFastY90Kernel::SampleAngle(double energy, double probability,
                                      double binFraction) const {
  const auto &cdf = GetConditionalCDFs().angle[ConditionalEnergyBin(energy)];
  return (FindBin(cdf, probability) + binFraction) * std::acos(-1.0) / 180;
}
