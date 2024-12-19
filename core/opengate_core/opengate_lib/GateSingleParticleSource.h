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
#include "G4VPrimaryGenerator.hh"
#include "GateAcceptanceAngleTester.h"
#include "GateAcceptanceAngleTesterManager.h"
#include "GateHelpers.h"
#include "GateRandomMultiGauss.h"
#include "GateSPSAngDistribution.h"
#include "GateSPSEneDistribution.h"
#include "GateSPSPosDistribution.h"

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

  GateSPSAngDistribution *GetAngDist() { return fDirectionGenerator; }

  GateSPSEneDistribution *GetEneDist() { return fEnergyGenerator; }

  virtual void SetPosGenerator(GateSPSPosDistribution *pg);

  void SetParticleDefinition(G4ParticleDefinition *def);

  void SetAAManager(GateAcceptanceAngleTesterManager *aa_manager);

  void GeneratePrimaryVertex(G4Event *evt) override;

  G4ThreeVector GenerateDirectionWithAA(const G4ThreeVector &position,
                                        bool &accept);

  void GeneratePrimaryVertexBackToBack(G4Event *event, G4ThreeVector &position,
                                       G4ThreeVector &direction, double energy);

  void SetBackToBackMode(bool flag, bool accolinearityFlag);

  // Probably an underestimation in most cases, but it is the most cited
  // value (Moses 2011)
  void SetAccolinearityFWHM(double accolinearityFWHM);

protected:
  G4ParticleDefinition *fParticleDefinition;
  double fCharge;
  double fMass;
  GateSPSPosDistribution *fPositionGenerator;
  GateSPSAngDistribution *fDirectionGenerator;
  GateSPSEneDistribution *fEnergyGenerator;
  G4SPSRandomGenerator *fBiasRndm;
  bool fAccolinearityFlag;
  bool fBackToBackMode;
  double fAccolinearitySigma;

  // for acceptance angle
  GateAcceptanceAngleTesterManager *fAAManager;
};

#endif // GateSingleParticleSource_h
