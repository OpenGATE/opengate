/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSPSPosDistribution_h
#define GateSPSPosDistribution_h

#include "G4SPSPosDistribution.hh"
#include "G4ParticleDefinition.hh"

class GateSPSPosDistribution : public G4SPSPosDistribution {

public:

    virtual ~GateSPSPosDistribution() {}

    // Cannot inherit from GenerateOne, so we consider VGenerateOne instead
    virtual G4ThreeVector VGenerateOne();

};

#endif // GateSPSPosDistribution_h
