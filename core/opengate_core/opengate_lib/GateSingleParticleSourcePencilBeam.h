/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GatePencilBeamSingleParticleSource_h
#define GatePencilBeamSingleParticleSource_h

#include "GateSingleParticleSource.h"
#include <pybind11/stl.h>

#include "GateRandomMultiGauss.h"

/*
    Single Particle Source generator specific for PencilBeam source
*/

class GateGenericSource;

namespace py = pybind11;

class GateSingleParticleSourcePencilBeam : public GateSingleParticleSource {

public:
  GateSingleParticleSourcePencilBeam(std::string motherVolume, std::string);

  void GeneratePrimaryVertex(G4Event *evt) override;

  void SetPBSourceParam(py::dict puser_info);

  void PhaseSpace(double sigma, double theta, double epsilon, double conv,
                  std::vector<double> &symM);

  void SetSourceRotTransl(G4ThreeVector t, G4RotationMatrix r);

protected:
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

  GateRandomMultiGauss *mGaussian2DXTheta =
      new GateRandomMultiGauss(mUXTheta, mSXTheta);
  GateRandomMultiGauss *mGaussian2DYPhi =
      new GateRandomMultiGauss(mUYPhi, mSYPhi);
};

#endif // GatePencilBeamSingleParticleSource_h
