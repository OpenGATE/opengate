/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSingleParticleSource_h
#define GateSingleParticleSource_h

#include "G4AffineTransform.hh"
#include "G4ParticleDefinition.hh"
#include "G4SPSAngDistribution.hh"
#include "G4VPrimaryGenerator.hh"
#include "GateAcceptanceAngleTester.h"
#include "GateAcceptanceAngleTesterManager.h"
#include "GateHelpers.h"
#include "GateSPSEneDistribution.h"
#include "GateSPSPosDistribution.h"

#include "GateRandomMultiGauss.h"

/*
    Single Particle Source generator.
    We need to re-implement the one from G4 in order to
    replace SPSPos/Ang/Ene generator by different ones
*/

class GateGenericSource;

class GateSingleParticleSource : public G4VPrimaryGenerator {

public:
  explicit GateSingleParticleSource(std::string mother_volume);

  ~GateSingleParticleSource() override;

  GateSPSPosDistribution *GetPosDist() { return fPositionGenerator; }

  G4SPSAngDistribution *GetAngDist() { return fDirectionGenerator; }

  GateSPSEneDistribution *GetEneDist() { return fEnergyGenerator; }

  virtual void SetPosGenerator(GateSPSPosDistribution *pg);

  void SetParticleDefinition(G4ParticleDefinition *def);

  void SetAAManager(GateAcceptanceAngleTesterManager *aa_manager);

  void GeneratePrimaryVertex(G4Event *evt) override;

  G4ThreeVector GenerateDirectionWithAA(const G4ThreeVector &position,
                                        bool &accept);

protected:
  G4ParticleDefinition *fParticleDefinition;
  double fCharge;
  double fMass;
  GateSPSPosDistribution *fPositionGenerator;
  G4SPSAngDistribution *fDirectionGenerator;
  GateSPSEneDistribution *fEnergyGenerator;
  G4SPSRandomGenerator *fBiasRndm;

  // for acceptance angle
  GateAcceptanceAngleTesterManager *fAAManager;
};

#endif // GateSingleParticleSource_h
