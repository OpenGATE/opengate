/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateHitsCollectionActor_h
#define GateHitsCollectionActor_h

#include "../GateVActor.h"
#include "GateDigiCollection.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateDigitizerHitsCollectionActor : public GateVActor {

public:
  explicit GateDigitizerHitsCollectionActor(py::dict &user_info);

  ~GateDigitizerHitsCollectionActor() override;

  void InitializeUserInfo(py::dict &user_info) override;

  void InitializeCpp() override;

  // Called when the simulation starts (master thread only)
  void StartSimulationAction() override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  // Called every time an Event starts
  void BeginOfEventAction(const G4Event *event) override;

  // Called every time a batch of steps must be processed
  void SteppingAction(G4Step * /*unused*/) override;

  // Called every time a Run ends (all threads)
  void EndOfRunAction(const G4Run *run) override;

  // Called by every worker when the simulation is about to end
  void EndOfSimulationWorkerAction(const G4Run * /*lastRun*/) override;

  // Called when the simulation ends (master thread only)
  void EndSimulationAction() override;

protected:
  std::string fHitsCollectionName;
  std::vector<std::string> fUserDigiAttributeNames;
  GateDigiCollection *fHits{};
  bool fDebug{};
  bool fKeepZeroEdep{};
  int fClearEveryNEvents{};
};

#endif // GateHitsCollectionActor_h
