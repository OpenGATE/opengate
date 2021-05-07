/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSPSPosDistribution_h
#define GamSPSPosDistribution_h

#include "G4SPSPosDistribution.hh"
#include "G4ParticleDefinition.hh"

class GamSPSPosDistribution : public G4SPSPosDistribution {

public:

    virtual ~GamSPSPosDistribution() {}

    // Cannot inherit from GenerateOne
    virtual G4ThreeVector VGenerateOne();

};

#endif // GamSPSPosDistribution_h
