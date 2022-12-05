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
#include <pybind11/embed.h>

#include "GateRandomMultiGauss.h"

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

  void SetAAManager(GateAcceptanceAngleTesterManager *aa_manager);

  void GeneratePrimaryVertex(G4Event *evt) override;

  void GeneratePrimaryVertexPB(G4Event *evt);

  void SetPBSourceParam(py::dict puser_info);

  void PhaseSpace(double sigma, double theta, double epsilon, double conv,
                  std::vector<double> &symM);

  void SetSourceRotTransl(G4ThreeVector t, G4RotationMatrix r);

protected:
  G4ParticleDefinition *fParticleDefinition;
  double fCharge;
  double fMass;
  GateSPSPosDistribution *fPositionGenerator;
  G4SPSAngDistribution *fDirectionGenerator;
  GateSPSEneDistribution *fEnergyGenerator;
  G4SPSRandomGenerator *fBiasRndm;

  // for acceptance angle
  /*std::map<std::string, std::string> fAcceptanceAngleParam;
  std::vector<GateAcceptanceAngleTester *> fAATesters;
  std::vector<std::string> fAcceptanceAngleVolumeNames;
  bool fEnabledFlag;
  unsigned long fNotAcceptedEvents;
  int fAALastRunId;*/
  GateAcceptanceAngleTesterManager *fAAManager;
  double fEffectiveEventTime;

  // PBS specific parameters
  bool mIsInitialized = false;
  double sigmaX, sigmaY, thetaX, thetaY, epsilonX, epsilonY, convX, convY;
  G4ThreeVector source_transl;
  G4RotationMatrix source_rot;

  // Gaussian distribution generation for direction
  std::vector<double> mUXTheta = {0, 0};
  std::vector<double> mUYPhi = {0, 0};
  std::vector<double> mSXTheta = {0, 0, 0, 0};
  std::vector<double> mSYPhi = {0, 0, 0, 0};

  GateRandomMultiGauss *MultiGauss = new GateRandomMultiGauss(mUYPhi, mSYPhi);
  GateRandomMultiGauss *mGaussian2DXTheta =
      new GateRandomMultiGauss(mUXTheta, mSXTheta);
  GateRandomMultiGauss *mGaussian2DYPhi =
      new GateRandomMultiGauss(mUYPhi, mSYPhi);
};

#endif // GateSingleParticleSource_h
