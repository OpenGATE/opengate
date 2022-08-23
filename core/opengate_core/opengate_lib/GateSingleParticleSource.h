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
#include "GateHelpers.h"
#include "GateSPSEneDistribution.h"
#include "GateSPSPosDistribution.h"
#include <pybind11/embed.h>

/*
    Single Particle Source generator.
    We need to re-implement the one from G4 in order to
    replace SPSPos/Ang/Ene generator by different ones
*/

class GateGenericSource;

namespace py = pybind11;

class GateSingleParticleSource : public G4VPrimaryGenerator {

public:
  GateSingleParticleSource(std::string mother_volume);

  ~GateSingleParticleSource() override;

  G4SPSPosDistribution *GetPosDist() { return fPositionGenerator; }

  G4SPSAngDistribution *GetAngDist() { return fDirectionGenerator; }

  GateSPSEneDistribution *GetEneDist() { return fEnergyGenerator; }

  void SetPosGenerator(GateSPSPosDistribution *pg);

  void SetParticleDefinition(G4ParticleDefinition *def);

  bool TestIfAcceptAngle(const G4ThreeVector &position,
                         const G4ThreeVector &momentum_direction);

  void GeneratePrimaryVertex(G4Event *evt) override;

  void InitializeAcceptanceAngle();

  void SetAcceptanceAngleParam(py::dict puser_info);

  unsigned long GetAASkippedParticles() const { return fAASkippedParticles; }

protected:
  G4ParticleDefinition *fParticleDefinition;
  double fCharge;
  double fMass;
  GateSPSPosDistribution *fPositionGenerator;
  G4SPSAngDistribution *fDirectionGenerator;
  GateSPSEneDistribution *fEnergyGenerator;
  G4SPSRandomGenerator *fBiasRndm;

  // for acceptance angle
  std::map<std::string, std::string> fAcceptanceAngleParam;
  std::vector<GateAcceptanceAngleTester *> fAATesters;
  std::vector<std::string> fAcceptanceAngleVolumeNames;
  bool fAcceptanceAngleFlag;
  unsigned long fAASkippedParticles;
  int fAALastRunId;
};

#endif // GateSingleParticleSource_h
