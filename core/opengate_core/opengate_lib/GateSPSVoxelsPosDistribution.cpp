/* --------------------------------------------------
   Copyright (C): OpenGate Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSPSVoxelsPosDistribution.h"
#include "GateHelpers.h"
#include <Randomize.hh>
#include <limits>
#include <memory>

GateSPSVoxelsPosDistribution::GateSPSVoxelsPosDistribution() {
  // Create the image pointer
  // The size and allocation will be performed on the py side
  cpp_image = ImageType::New();

  // default position
  fGlobalTranslation = G4ThreeVector();
  fGlobalRotation = G4RotationMatrix();
}

void GateSPSVoxelsPosDistribution::SetCumulativeDistributionFunction(
    const double *cdfZ, const double *cdfY, const double *cdfX, std::size_t nx,
    std::size_t ny, std::size_t nz) {
  if (nx * ny * nz >= std::numeric_limits<std::uint32_t>::max()) {
    Fatal("GateSPSVoxelsPosDistribution: too many voxels in the image");
  }

  // probability of each voxel (z, y, x) from the CDFs: cdfZ[z], cdfY[z, y]
  // (along y, for each z) and cdfX[z, y, x] (along x, for each z and y)
  std::vector<double> proba;
  std::vector<std::uint32_t> index;
  for (std::size_t i = 0; i < nz; i++) {
    const double pz = cdfZ[i] - (i > 0 ? cdfZ[i - 1] : 0.0);
    if (pz <= 0)
      continue;
    for (std::size_t j = 0; j < ny; j++) {
      const std::size_t row = i * ny + j;
      const double py = cdfY[row] - (j > 0 ? cdfY[row - 1] : 0.0);
      if (py <= 0)
        continue;
      for (std::size_t k = 0; k < nx; k++) {
        const std::size_t v = row * nx + k;
        const double px = cdfX[v] - (k > 0 ? cdfX[v - 1] : 0.0);
        if (px <= 0)
          continue;
        proba.push_back(pz * py * px);
        index.push_back(static_cast<std::uint32_t>(v));
      }
    }
  }
  if (proba.empty()) {
    Fatal("GateSPSVoxelsPosDistribution: all the voxels have a zero "
          "probability");
  }

  // alias table (Vose): the probabilities scaled to a mean of 1
  const std::size_t n = proba.size();
  double total = 0;
  for (const auto p : proba)
    total += p;
  std::vector<double> scaled(n);
  std::vector<std::size_t> small, large;
  auto table = std::make_shared<GateVoxelAliasTable>();
  table->nx = nx;
  table->ny = ny;
  table->nz = nz;
  auto &alias = table->entries;
  alias.assign(n, GateVoxelAliasTable::Entry{1.0f, 0, 0});
  for (std::size_t m = 0; m < n; m++) {
    scaled[m] = proba[m] * static_cast<double>(n) / total;
    (scaled[m] < 1.0 ? small : large).push_back(m);
    alias[m].self = index[m];
    alias[m].alias = index[m];
  }
  while (!small.empty() && !large.empty()) {
    const auto s = small.back();
    small.pop_back();
    const auto l = large.back();
    alias[s].q = static_cast<float>(scaled[s]);
    alias[s].alias = index[l];
    scaled[l] = (scaled[l] + scaled[s]) - 1.0;
    if (scaled[l] < 1.0) {
      large.pop_back();
      small.push_back(l);
    }
  }
  // the remaining entries (rounding): keep their own voxel
  for (const auto m : small)
    alias[m].q = 1.0f;
  for (const auto m : large)
    alias[m].q = 1.0f;
  fTable = table;
}

void GateSPSVoxelsPosDistribution::SetAliasTable(
    std::shared_ptr<GateVoxelAliasTable> table) {
  if (table == nullptr || table->entries.empty()) {
    Fatal("GateSPSVoxelsPosDistribution: empty alias table");
  }
  fTable = table;
}

G4ThreeVector GateSPSVoxelsPosDistribution::VGenerateOne() {
  // alias sampling: an entry m uniformly, then its voxel with the
  // probability q, otherwise its alias voxel
  const auto &t = *fTable;
  const double u = G4UniformRand() * static_cast<double>(t.entries.size());
  auto m = static_cast<std::size_t>(u);
  if (m >= t.entries.size())
    m = t.entries.size() - 1;
  const auto &e = t.entries[m];
  const std::uint32_t v = (u - static_cast<double>(m)) < e.q ? e.self : e.alias;
  const auto k = static_cast<itk::IndexValueType>(v % t.nx);
  const auto j = static_cast<itk::IndexValueType>((v / t.nx) % t.ny);
  const auto i = static_cast<itk::IndexValueType>(v / (t.nx * t.ny));

  const itk::Index<3> index = {k, j, i};
  itk::Point<double> point;
  cpp_image->TransformIndexToPhysicalPoint(index, point);

  // random position within a voxel
  point[0] += (G4UniformRand() - 0.5) * cpp_image->GetSpacing()[0];
  point[1] += (G4UniformRand() - 0.5) * cpp_image->GetSpacing()[1];
  point[2] += (G4UniformRand() - 0.5) * cpp_image->GetSpacing()[2];

  // convert to G4 vector and move it according to mother volume
  G4ThreeVector position(point[0], point[1], point[2]);
  position = fGlobalRotation * position +
             fGlobalTranslation; // not global only according to mother ?

  return position;
}
