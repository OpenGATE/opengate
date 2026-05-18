/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateLastVertexSource_h
#define GateLastVertexSource_h

#include "GateLastVertexSplittingDataContainer.h"
#include "GateSingleParticleSource.h"
#include "GateVSource.h"
#include <pybind11/stl.h>

namespace py = pybind11;

/*
 This is NOT a real source type but a template to help writing your own source
 type. Copy-paste this file with a different name ("MyNewSource.hh") and start
 building. You also need to copy : GateLastVertexSource.hh
 GateLastVertexSource.cpp pyGateLastVertexSource.cpp And add the source
 declaration in opengate_core.cpp
 */

class GateLastVertexSource : public GateVSource {

public:
  GateLastVertexSource();

  ~GateLastVertexSource() override;

  void InitializeUserInfo(py::dict &user_info) override;

  double PrepareNextTime(double current_simulation_time,
                         double NumberOfGeneratedEvents) override;

  void PrepareNextRun() override;

  void GeneratePrimaries(G4Event *event, double time) override;

  void GenerateOnePrimary(G4Event *event, double time, G4int idx);

  void SetListOfVertexToSimulate(std::vector<LastVertexDataContainer> list) {
    fListOfContainer = list;
  }

  void SetNumberOfGeneratedEvent(G4int nbEvent) {
    fNumberOfGeneratedEvents = nbEvent;
  }

  void SetNumberOfEventToSimulate(G4int N) { fN = N; }

  G4int GetNumberOfEventToSimulate() { return fN; }

  G4int GetNumberOfGeneratedEvent() { return fNumberOfGeneratedEvents; }

  G4String GetProcessToSplit() { return fProcessToSplit; }

  LastVertexDataContainer GetLastVertexContainer() { return fContainer; }

protected:
  G4int fNumberOfGeneratedEvents = 0;
  G4int fN = 0;
  double fFloatValue;
  std::vector<double> fVectorValue;
  std::vector<LastVertexDataContainer> fListOfContainer;
  G4String fProcessToSplit = "None";
  LastVertexDataContainer fContainer;
};

#endif // GateLastVertexSource_h
