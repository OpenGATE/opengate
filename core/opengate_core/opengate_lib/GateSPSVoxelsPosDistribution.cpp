/* --------------------------------------------------
   Copyright (C): OpenGate Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSPSVoxelsPosDistribution.h"
#include <Randomize.hh>

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
  fCDFZ.assign(cdfZ, cdfZ + nz);
  fCDFY.assign(cdfY, cdfY + nz * ny);
  fCDFX.assign(cdfX, cdfX + nz * ny * nx);
}

G4ThreeVector GateSPSVoxelsPosDistribution::VGenerateOne() {
  // G4UniformRand: default boundaries ]0.1[ for operator()().
  const auto imageSize = cpp_image->GetLargestPossibleRegion().GetSize();
  const auto nx = static_cast<int>(imageSize[0]);
  const auto ny = static_cast<int>(imageSize[1]);
  const auto nz = static_cast<int>(imageSize[2]);

  // Get Cumulative Distribution Function for Z
  auto i = 0;
  do {
    auto p = G4UniformRand();
    const auto lower = std::lower_bound(fCDFZ.begin(), fCDFZ.end(), p);
    i = std::distance(fCDFZ.begin(), lower);
  } while (i >= nz);

  // Get Cumulative Distribution Function for Y, knowing Z
  auto j = 0;
  do {
    auto p = G4UniformRand();
    const auto begin = fCDFY.begin() + i * ny;
    const auto lower = std::lower_bound(begin, begin + ny, p);
    j = std::distance(begin, lower);
  } while (j >= ny);

  // Get Cumulative Distribution Function for X, knowing X and Y
  auto k = 0;
  do {
    auto p = G4UniformRand();
    const auto begin = fCDFX.begin() + (i * ny + j) * nx;
    const auto lower = std::lower_bound(begin, begin + nx, p);
    k = std::distance(begin, lower);
  } while (k >= nx);

  // convert to physical coordinate
  // (warning to the numpy order Z Y X)
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
