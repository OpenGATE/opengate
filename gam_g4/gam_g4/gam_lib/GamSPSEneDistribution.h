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

    void GenerateFromCDF();

    void GenerateFluor18();

    void GenerateOxygen15();

    void GenerateCarbon11();

    // Cannot inherit from GenerateOne
    virtual G4double VGenerateOne(G4ParticleDefinition *);

    double fParticleEnergy;

    std::vector<double> fProbabilityCDF;
    std::vector<double> fEnergyCDF;

};

#endif // GamSPSEneDistribution_h
