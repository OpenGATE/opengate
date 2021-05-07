/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSPSVoxelsPosDistribution_h
#define GamSPSVoxelsPosDistribution_h

#include <utility>

#include "G4ParticleDefinition.hh"
#include "GamSPSPosDistribution.h"

class GamSPSVoxelsPosDistribution : public GamSPSPosDistribution {

public:

    virtual ~GamSPSVoxelsPosDistribution() {}

    // Cannot inherit from GenerateOne
    virtual G4ThreeVector VGenerateOne();

    typedef std::vector<double> VD;
    typedef std::vector<VD> VD2;
    typedef std::vector<std::vector<VD>> VD3;

    void SetCumulativeDistributionFunction(VD vz, VD2 vy, VD3 vx);

    void SetTranslation(G4ThreeVector v) { fTranslation = v; }

    void SetImageSpacing(VD spacing) { fSpacing = std::move(spacing); }

    VD3 fCDFX;
    VD2 fCDFY;
    VD fCDFZ;
    std::vector<double> fSpacing;
    G4ThreeVector fTranslation;
};

#endif // GamSPSVoxelsPosDistribution_h
