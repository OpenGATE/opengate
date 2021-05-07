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
    /*
     * Warning : this is a COPY ov v
     */
    DDD("set Z Y");
    fCDFZ = vz;
    fCDFY = vy;
    fCDFX = vx;
    DDD(vz.size());
    DDD(vy.size());
    DDD(vy[0].size());
    DDD(vx.size());
    DDD(vx[0].size());
    DDD(vx[0][0].size());
}

G4ThreeVector GamSPSVoxelsPosDistribution::VGenerateOne() {
    // Get Cumulative Distribution Function for Z
    int i = 0;
    auto p = G4UniformRand();
    //DDD(p);
    while (p > fCDFZ[i]) i++;
    //DD(i);

    // Get Cumulative Distribution Function for Y, knowing Z
    int j = 0;
    p = G4UniformRand();
    //DDD(p);
    while (p > fCDFY[i][j]) j++;
    //DD(j);

    // Get Cumulative Distribution Function for X, knowing X and Y
    int k = 0;
    p = G4UniformRand();
    //DDD(p);
    while (p > fCDFX[i][j][k]) k++;

    //DDD(i);
    //DDD(j);
    //DDD(k);
    G4ThreeVector centered(fSpacing[0] * fCDFX[0][0].size() / 2.0,
                           fSpacing[1] * fCDFY[0].size() / 2.0,
                           fSpacing[2] * fCDFZ.size() / 2.0);
    //DDD(centered);

    G4ThreeVector position(
        fSpacing[0] * (k + G4UniformRand()) - fSpacing[0] / 2.0 - centered[0] + fTranslation[0],
        fSpacing[1] * (j + G4UniformRand()) - fSpacing[1] / 2.0 - centered[1] + fTranslation[1],
        fSpacing[2] * (i + G4UniformRand()) - fSpacing[2] / 2.0 - centered[2] + fTranslation[2]);
    //DDD(position);

    // FIXME translation, rotation ???

    //return position;
    return position;
}
