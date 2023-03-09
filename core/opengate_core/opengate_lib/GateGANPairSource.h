/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateGANPairSource_h
#define GateGANPairSource_h

#include "GateGANSource.h"
#include "GateSPSVoxelsPosDistribution.h"
#include "GateSingleParticleSource.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateGANPairSource : public GateGANSource {

public:
  GateGANPairSource();

  ~GateGANPairSource() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void SetGeneratorInfo(py::dict &user_info) override;

  void GeneratePrimaries(G4Event *event,
                         double current_simulation_time) override;

  void GeneratePrimariesPair(G4Event *event, double current_simulation_time);

  // For pairs of particles
  std::vector<double> fPositionX2;
  std::vector<double> fPositionY2;
  std::vector<double> fPositionZ2;

  std::vector<double> fDirectionX2;
  std::vector<double> fDirectionY2;
  std::vector<double> fDirectionZ2;

  std::vector<double> fEnergy2;
  std::vector<double> fWeight2;
  std::vector<double> fTime2;
};

#endif // GateGANPairSource_h
