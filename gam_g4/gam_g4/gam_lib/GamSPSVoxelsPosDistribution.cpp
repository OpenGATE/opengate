/* --------------------------------------------------
   Copyright (C): OpenGate Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <Randomize.hh>
#include "GamSPSVoxelsPosDistribution.h"
#include "GamHelpers.h"

GamSPSVoxelsPosDistribution::GamSPSVoxelsPosDistribution() {
    // Create the image pointer
    // The size and allocation will be performed on the py side
    cpp_image = ImageType::New();

    // default position
    fGlobalTranslation = G4ThreeVector();
    fGlobalRotation = G4RotationMatrix();
}

void GamSPSVoxelsPosDistribution::SetCumulativeDistributionFunction(VD vz, VD2 vy, VD3 vx) {
    // Warning : this is a COPY of all cumulative distribution functions
    fCDFZ = vz;
    fCDFY = vy;
    fCDFX = vx;
}

G4ThreeVector GamSPSVoxelsPosDistribution::VGenerateOne() {
    // G4UniformRand : default boundaries ]0.1[ for operator()().

    // Get Cumulative Distribution Function for Z
    auto p = G4UniformRand();
    auto lower = std::lower_bound(fCDFZ.begin(), fCDFZ.end(), p);
    auto i = std::distance(fCDFZ.begin(), lower);

    // Get Cumulative Distribution Function for Y, knowing Z
    p = G4UniformRand();
    lower = std::lower_bound(fCDFY[i].begin(), fCDFY[i].end(), p);
    auto j = std::distance(fCDFY[i].begin(), lower);

    // Get Cumulative Distribution Function for X, knowing X and Y
    p = G4UniformRand();
    lower = std::lower_bound(fCDFX[i][j].begin(), fCDFX[i][j].end(), p);
    auto k = std::distance(fCDFX[i][j].begin(), lower);

    // convert to physical coordinate
    // (warning to the numpy order Z Y X)
    itk::Index<3> index = {k,j,i};
    itk::Point<double, 3> point;
    cpp_image->TransformIndexToPhysicalPoint(index, point);

    // random position within a voxel
    point[0] += G4UniformRand() - 0.5 * cpp_image->GetSpacing()[0];
    point[1] += G4UniformRand() - 0.5 * cpp_image->GetSpacing()[1];
    point[2] += G4UniformRand() - 0.5 * cpp_image->GetSpacing()[2];

    // convert to G4 vector and move according to mother volume
    G4ThreeVector position(point[0], point[1], point[2]);
    position = fGlobalRotation * position + fGlobalTranslation;

    return position;
}

