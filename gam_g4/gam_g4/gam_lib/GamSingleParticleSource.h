/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSingleParticleSource_h
#define GamSingleParticleSource_h

#include "G4AffineTransform.hh"
#include "G4ParticleDefinition.hh"
#include "G4SPSAngDistribution.hh"
#include "G4VPrimaryGenerator.hh"
#include "GamAcceptanceAngleTester.h"
#include "GamHelpers.h"
#include "GamSPSEneDistribution.h"
#include "GamSPSPosDistribution.h"
#include <pybind11/embed.h>

#include "GamRandomMultiGauss.h"

/*
    Single Particle Source generator.
    We need to re-implement the one from G4 in order to
    replace SPSPos/Ang/Ene generator by different ones
*/

class GamGenericSource;

namespace py = pybind11;

class GamSingleParticleSource : public G4VPrimaryGenerator {

public:
  GamSingleParticleSource(std::string mother_volume);

  ~GamSingleParticleSource() override;

  G4SPSPosDistribution *GetPosDist() { return fPositionGenerator; }

  G4SPSAngDistribution *GetAngDist() { return fDirectionGenerator; }

  GamSPSEneDistribution *GetEneDist() { return fEnergyGenerator; }

  void SetPosGenerator(GamSPSPosDistribution *pg);

  void SetParticleDefinition(G4ParticleDefinition *def);

  bool TestIfAcceptAngle(const G4ThreeVector &position,
                         const G4ThreeVector &momentum_direction);

  void GeneratePrimaryVertex(G4Event *evt) override;

  void GeneratePrimaryVertexPB(G4Event *evt);

  void InitializeAcceptanceAngle();

  void SetAcceptanceAngleParam(py::dict puser_info);

  void SetPBSourceParam(py::dict puser_info);

  unsigned long GetAASkippedParticles() const { return fAASkippedParticles; }

  void PhaseSpace(double sigma, double theta, double epsilon, double conv,
                  vector<double> &symM);

  void SetSourceRotTransl(G4ThreeVector t, G4RotationMatrix r);

protected:
  G4ParticleDefinition *fParticleDefinition;
  double fCharge;
  double fMass;
  GamSPSPosDistribution *fPositionGenerator;
  G4SPSAngDistribution *fDirectionGenerator;
  GamSPSEneDistribution *fEnergyGenerator;
  G4SPSRandomGenerator *fBiasRndm;

  // for acceptance angle
  std::map<std::string, std::string> fAcceptanceAngleParam;
  std::vector<GamAcceptanceAngleTester *> fAATesters;
  std::vector<std::string> fAcceptanceAngleVolumeNames;
  bool fAcceptanceAngleFlag;
  unsigned long fAASkippedParticles;
  int fAALastRunId;

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

  GamRandomMultiGauss *MultiGauss = new GamRandomMultiGauss(mUYPhi, mSYPhi);
  GamRandomMultiGauss *mGaussian2DXTheta =
      new GamRandomMultiGauss(mUXTheta, mSXTheta);
  GamRandomMultiGauss *mGaussian2DYPhi =
      new GamRandomMultiGauss(mUYPhi, mSYPhi);
};

#endif // GamSingleParticleSource_h
