/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateLastVertexSource_h
#define GateLastVertexSource_h

#include "GateLastVertexSplittingDataContainer.h"
#include "GateVSource.h"
#include <pybind11/stl.h>

namespace py = pybind11;

// Replays the last-vertex states published by the splitting actor.

class GateLastVertexSource : public GateVSource {

public:
  GateLastVertexSource();

  ~GateLastVertexSource() override;

  void InitializeUserInfo(py::dict &user_info) override;

  double PrepareNextTime(double current_simulation_time,
                         unsigned long NumberOfGeneratedEvents) override;

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
  std::vector<LastVertexDataContainer> fListOfContainer;
  G4String fProcessToSplit = "None";
  LastVertexDataContainer fContainer;
};

#endif // GateLastVertexSource_h
