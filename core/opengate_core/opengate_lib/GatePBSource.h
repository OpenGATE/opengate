/* --------------------------------------------------
   Copyright (C): OpenGate Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GatePBSource_h
#define GatePBSource_h

#include "GateGenericSource.h"
#include "GateSingleParticleSource.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GatePBSource : public GateGenericSource {

public:
  GatePBSource();

  virtual ~GatePBSource();

  void InitializeUserInfo(py::dict &user_info) override;

  void GeneratePrimaries(G4Event *event, double time) override;

  void InitializePosition(py::dict puser_info) override;

  void PrepareNextRun() override;

protected:
};

#endif // GatePBSource_h
