/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSPSEneDistribution_h
#define GamSPSEneDistribution_h

#include "G4SPSEneDistribution.hh"

class GamSPSEneDistribution : public G4SPSEneDistribution {

public:

    virtual ~GamSPSEneDistribution() {}

    void GenerateFluor18();

    void GenerateOxygen15();

    void GenerateCarbon11();

    // FIXME see GamSingleParticleSource
    virtual G4double GenerateOne_modified(G4ParticleDefinition *);

    double fParticleEnergy;

    G4Mutex mutex;
    // This can be a shared resource.

};

#endif // GamSPSEneDistribution_h
