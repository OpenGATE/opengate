/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVoxelSource_h
#define GateVoxelSource_h

#include "GateGenericSource.h"
#include "GateSPSVoxelsPosDistribution.h"
#include "GateSingleParticleSource.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateVoxelSource : public GateGenericSource {

public:
  GateVoxelSource();

  ~GateVoxelSource() override;

  void PrepareNextRun() override;

  GateSPSVoxelsPosDistribution *GetSPSVoxelPosDistribution() {
    return fVoxelPositionGenerator;
  }

protected:
  void InitializePosition(py::dict user_info) override;

  GateSPSVoxelsPosDistribution *fVoxelPositionGenerator;
};

#endif // GateVoxelSource_h
