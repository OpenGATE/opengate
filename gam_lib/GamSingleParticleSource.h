/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSingleParticleSource_h
#define GamSingleParticleSource_h

#include "GamHelpers.h"
#include "G4VPrimaryGenerator.hh"
#include "G4SPSAngDistribution.hh"
#include "GamSPSPosDistribution.h"
#include "GamSPSEneDistribution.h"
#include "G4ParticleDefinition.hh"

/*
    Single Particle Source generator.
    We need to re-implement the one from G4 in order to
    replace SPSPos/Ang/Ene generator by different ones
*/

class GamSingleParticleSource : public G4VPrimaryGenerator {

public:

    GamSingleParticleSource();

    virtual ~GamSingleParticleSource();

    G4SPSPosDistribution *GetPosDist() { return fPositionGenerator; }

    G4SPSAngDistribution *GetAngDist() { return fDirectionGenerator; }

    GamSPSEneDistribution *GetEneDist() { return fEnergyGenerator; }

    void SetPosGenerator(GamSPSPosDistribution *pg);

    void SetParticleDefinition(G4ParticleDefinition *def);

    virtual void GeneratePrimaryVertex(G4Event *evt);

protected:
    G4ParticleDefinition *fParticleDefinition;
    double fCharge;
    double fMass;
    GamSPSPosDistribution *fPositionGenerator;
    G4SPSAngDistribution *fDirectionGenerator;
    GamSPSEneDistribution *fEnergyGenerator;
    G4SPSRandomGenerator *fBiasRndm;
};

#endif // GamSingleParticleSource_h
