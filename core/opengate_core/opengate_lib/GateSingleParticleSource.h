/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSingleParticleSource_h
#define GateSingleParticleSource_h

#include "G4ParticleDefinition.hh"
#include "G4VPrimaryGenerator.hh"
#include "GateAcceptanceAngleManager.h"
#include "GateHelpers.h"
#include "GateSPSAngDistribution.h"
#include "GateSPSEneDistribution.h"
#include "GateSPSPosDistribution.h"
#include "biasing/GateForcedDirectionManager.h"

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

  GateSPSPosDistribution *GetPosDist() const { return fPositionGenerator; }

  GateSPSAngDistribution *GetAngDist() const { return fDirectionGenerator; }

  GateSPSEneDistribution *GetEneDist() const { return fEnergyGenerator; }

  virtual void SetPosGenerator(GateSPSPosDistribution *pg);

  void SetParticleDefinition(G4ParticleDefinition *def);

  void SetAAManager(GateAcceptanceAngleManager *aa_manager);

  void SetFDManager(GateForcedDirectionManager *fd_manager);

  void GeneratePrimaryVertex(G4Event *event) override;

  G4ThreeVector GenerateDirectionWithAA(const G4ThreeVector &position,
                                        bool &zero_energy_flag) const;

  void GeneratePrimaryVertexBackToBack(G4Event *event,
                                       const G4ThreeVector &position,
                                       const G4ThreeVector &direction,
                                       double energy) const;

  void SetBackToBackMode(bool flag, bool accolinearityFlag);

  void SetPolarization(G4ThreeVector &polarization);

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
  G4ThreeVector fPolarization;
  bool fPolarizationFlag;

  // for acceptance angle
  GateAcceptanceAngleManager *fAAManager;
  GateForcedDirectionManager *fFDManager;
};

#endif // GateSingleParticleSource_h
