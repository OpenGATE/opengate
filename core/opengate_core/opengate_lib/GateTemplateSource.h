/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateTemplateSource_h
#define GateTemplateSource_h

#include "GateAcceptanceAngleManager.h"
#include "GateSingleParticleSource.h"
#include "GateVSource.h"
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 This is NOT a real source type but a template to help writing your own source
 type. Copy-paste this file with a different name ("MyNewSource.hh") and start
 building. You also need to copy : GateTemplateSource.hh GateTemplateSource.cpp
 pyGateTemplateSource.cpp
 And add the source declaration in opengate_core.cpp
 */

class GateTemplateSource : public GateVSource {

public:
  GateTemplateSource();

  ~GateTemplateSource() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void PrepareNextRun() override;

  void GeneratePrimaries(G4Event *event, double time) override;

protected:
  unsigned long fNumberOfGeneratedEvents;
  unsigned long fN;
  double fFloatValue;
  std::vector<double> fVectorValue;
};

#endif // GateTemplateSource_h
