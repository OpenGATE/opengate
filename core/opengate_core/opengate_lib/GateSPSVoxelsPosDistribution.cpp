/* --------------------------------------------------
   Copyright (C): OpenGate Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSPSVoxelsPosDistribution.h"
#include "GateHelpers.h"
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
    const VD &vz, const VD2 &vy, const VD3 &vx) {
  // Warning: this is a COPY of all cumulative distribution functions
  fCDFZ = vz;
  fCDFY = vy;
  fCDFX = vx;
}

G4ThreeVector GateSPSVoxelsPosDistribution::VGenerateOne() {
  // G4UniformRand: default boundaries ]0.1[ for operator()().

  // Get Cumulative Distribution Function for Z
  auto i = 0;
  do {
    auto p = G4UniformRand();
    const auto lower = std::lower_bound(fCDFZ.begin(), fCDFZ.end(), p);
    i = std::distance(fCDFZ.begin(), lower);
  } while (i >= (int)fCDFX.size());

  // Get Cumulative Distribution Function for Y, knowing Z
  auto j = 0;
  do {
    auto p = G4UniformRand();
    const auto lower = std::lower_bound(fCDFY[i].begin(), fCDFY[i].end(), p);
    j = std::distance(fCDFY[i].begin(), lower);
  } while (j >= (int)fCDFX[i].size());

  // Get Cumulative Distribution Function for X, knowing X and Y
  auto k = 0;
  do {
    auto p = G4UniformRand();
    const auto lower =
        std::lower_bound(fCDFX[i][j].begin(), fCDFX[i][j].end(), p);
    k = std::distance(fCDFX[i][j].begin(), lower);
  } while (k >= (int)fCDFX[i][j].size());

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
