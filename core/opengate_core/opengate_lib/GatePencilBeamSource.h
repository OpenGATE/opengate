/* --------------------------------------------------
   Copyright (C): OpenGate Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GatePencilBeamSource_h
#define GatePencilBeamSource_h

#include "GateGenericSource.h"
#include "GateSingleParticleSourcePencilBeam.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GatePencilBeamSource : public GateGenericSource {

public:
  GatePencilBeamSource();

  ~GatePencilBeamSource() override;

  void InitializeDirection(py::dict puser_info) override;

  void PrepareNextRun() override;

protected:
  // the fSPS will be a GateSingleParticleSourcePencilBeam
  // we store the two pointers fSPS and fSPS_PB to the same object
  GateSingleParticleSourcePencilBeam *fSPS_PB;

  // void InitializeUserInfo(py::dict &user_info);
  void CreateSPS() override;
};

#endif // GatePencilBeamSource_h
