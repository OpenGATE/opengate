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

    // typedef for vector of vector
    typedef std::vector<double> VD;
    typedef std::vector<VD> VD2;
    typedef std::vector<std::vector<VD>> VD3;

    void SetCumulativeDistributionFunction(VD vz, VD2 vy, VD3 vx);

    void SetTranslation(VD t) { fTranslation = G4ThreeVector(t[0], t[1], t[2]); }

    void SetRotation(G4RotationMatrix r) { fRotation = r; }

    void SetImageCenter(VD t) { fImageCenter = G4ThreeVector(t[0], t[1], t[2]); }

    void SetImageSpacing(VD t) { fImageSpacing = G4ThreeVector(t[0], t[1], t[2]); }

    void InitializeOffset();

protected:
    VD3 fCDFX;
    VD2 fCDFY;
    VD fCDFZ;
    G4ThreeVector fImageSpacing;
    G4ThreeVector fImageCenter;
    G4ThreeVector fTranslation;
    G4RotationMatrix fRotation;

    G4ThreeVector fOffset;
};

#endif // GamSPSVoxelsPosDistribution_h
