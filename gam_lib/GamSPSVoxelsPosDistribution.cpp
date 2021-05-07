/* --------------------------------------------------
   Copyright (C): OpenGate Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <Randomize.hh>
#include "GamSPSVoxelsPosDistribution.h"
#include "GamHelpers.h"


void GamSPSVoxelsPosDistribution::SetCumulativeDistributionFunction(VD vz, VD2 vy, VD3 vx) {
    // Warning : this is a COPY of all cumulative distribution functions
    fCDFZ = vz;
    fCDFY = vy;
    fCDFX = vx;
}

void GamSPSVoxelsPosDistribution::InitializeOffset() {
    // the offset is composed of :
    // 1) image center, because by default volumes are centered
    // 2) half pixel offset (because we consider the side of the pixel + random [0:spacing]
    // 3) translation, provided by python part (for example to center in a CT)
    for (auto i = 0; i < 3; i++)
        fOffset[i] = -fImageSpacing[i] / 2.0 - fImageCenter[i] + fTranslation[i];
}

G4ThreeVector GamSPSVoxelsPosDistribution::VGenerateOne() {
    // Get Cumulative Distribution Function for Z
    int i = 0;
    auto p = G4UniformRand();
    while (p > fCDFZ[i]) i++;

    // Get Cumulative Distribution Function for Y, knowing Z
    int j = 0;
    p = G4UniformRand();
    while (p > fCDFY[i][j]) j++;

    // Get Cumulative Distribution Function for X, knowing X and Y
    int k = 0;
    p = G4UniformRand();
    while (p > fCDFX[i][j][k]) k++;

    G4ThreeVector position(
        fImageSpacing[0] * (k + G4UniformRand()) + fOffset[0],
        fImageSpacing[1] * (j + G4UniformRand()) + fOffset[1],
        fImageSpacing[2] * (i + G4UniformRand()) + fOffset[2]);

    // FIXME rotation
    return position;
}
