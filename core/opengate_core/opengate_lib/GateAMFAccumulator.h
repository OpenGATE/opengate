/* Copyright (C): OpenGATE Collaboration. LGPL; see LICENSE.md. */
#ifndef GateAMFAccumulator_h
#define GateAMFAccumulator_h

#include <array>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <vector>

// One worker's additive state, or the master's reduction target. Scientific
// means are derived only after the final raw merge; never merge finalized data.
struct AMFRawAccumulator {
  static constexpr size_t bins = 400;
  std::vector<double> dose;
  // Dose*yD, dose*yS, dose*alpha, dose*sqrt(beta), in that order.
  std::array<std::vector<double>, 4> moments;
  std::vector<double> spectra;
  bool finalized = false;
  bool consumed = false;

  /** Allocate zeroed dose and enabled numerators for a positive voxel count.
   * enabled orders yD, yS, alpha and sqrt(beta); spectra uses 400 bins/voxel.
   */
  AMFRawAccumulator(size_t voxels, const std::array<bool, 4> &enabled,
                    bool spectrum) {
    if (!voxels || voxels > std::numeric_limits<std::ptrdiff_t>::max() /
                                (bins * sizeof(double)))
      throw std::runtime_error("AMF: invalid accumulator dimensions");
    dose.resize(voxels, 0);
    for (size_t i = 0; i < moments.size(); ++i)
      if (enabled[i])
        moments[i].resize(voxels, 0);
    if (spectrum)
      spectra.resize(voxels * bins, 0);
  }

  /** Add compatible raw state exactly once and mark the source consumed.
   * Reject self, finalized or previously consumed inputs before touching sums.
   */
  void Merge(AMFRawAccumulator &other) {
    if (finalized || consumed || other.finalized || other.consumed ||
        this == &other)
      throw std::runtime_error("AMF: cannot merge finalized or self state");
    if (dose.size() != other.dose.size() ||
        spectra.size() != other.spectra.size())
      throw std::runtime_error("AMF: incompatible accumulator dimensions");
    for (size_t i = 0; i < moments.size(); ++i)
      if (moments[i].size() != other.moments[i].size())
        throw std::runtime_error("AMF: incompatible accumulator outputs");
    auto add = [](auto &a, const auto &b) {
      for (size_t i = 0; i < a.size(); ++i)
        a[i] += b[i];
    };
    add(dose, other.dose);
    for (size_t i = 0; i < moments.size(); ++i)
      add(moments[i], other.moments[i]);
    add(spectra, other.spectra);
    other.consumed = true;
  }

  /** Divide numerators by dose once, square mixed sqrt(beta), and zero empty
   * voxels. Dose stays an accumulated Gy value rather than a per-event average.
   */
  void Finalize() {
    if (finalized || consumed)
      throw std::runtime_error("AMF: duplicate or consumed finalization");
    for (size_t voxel = 0; voxel < dose.size(); ++voxel) {
      const double d = dose[voxel];
      if (!std::isfinite(d) || d < 0)
        throw std::runtime_error("AMF: nonfinite or negative accumulated dose");
      for (auto &moment : moments)
        if (!moment.empty())
          moment[voxel] = d > 0 ? moment[voxel] / d : 0;
      if (!moments[3].empty())
        moments[3][voxel] *= moments[3][voxel];
      if (!spectra.empty())
        for (size_t bin = 0; bin < bins; ++bin) {
          auto &value = spectra[voxel * bins + bin];
          value = d > 0 ? value / d : 0;
        }
    }
    finalized = true;
  }

  /** Free storage only after consumption or finalization; preserve lifecycle
   * flags. */
  void ReleaseBuffers() {
    if (!consumed && !finalized)
      throw std::runtime_error("AMF: cannot release active accumulator");
    std::vector<double>().swap(dose);
    std::vector<double>().swap(spectra);
    for (auto &moment : moments)
      std::vector<double>().swap(moment);
  }
};

#endif
