/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GatePhaseSpaceActor_h
#define GatePhaseSpaceActor_h

#include "G4Cache.hh"
#include "G4GenericAnalysisManager.hh"
#include "GateHelpers.h"
#include "GateVActor.h"
#include "digitizer/GateDigiCollection.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GatePhaseSpaceActor : public GateVActor {

public:
  // explicit GatePhaseSpaceActor(std::string type_name);
  explicit GatePhaseSpaceActor(py::dict &user_info);

  virtual ~GatePhaseSpaceActor();

  // Called when the simulation start (master thread only)
  void StartSimulationAction() override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  // Called every time a Event starts (all threads)
  void BeginOfEventAction(const G4Event *event) override;

  // Called at the beginning of every track
  void PreUserTrackingAction(const G4Track *track) override;

  // Called every time a batch of step must be processed
  void SteppingAction(G4Step *) override;

  // Called at the end of an event
  void EndOfEventAction(const G4Event *event) override;

  // Called every time a Run ends (all threads)
  void EndOfRunAction(const G4Run *run) override;

  void EndOfSimulationWorkerAction(const G4Run *run) override;

  // Called when the simulation end (master thread only)
  void EndSimulationAction() override;

  int GetNumberOfAbsorbedEvents();

  int GetTotalNumberOfEntries();

protected:
  // Local data for the threads (each one has a copy)
  struct threadLocalT {
    bool fCurrentEventHasBeenStored;
    bool fFirstStepInVolume;
  };
  G4Cache<threadLocalT> fThreadLocalData;

  std::string fOutputFilename;
  std::string fDigiCollectionName;
  std::vector<std::string> fUserDigiAttributeNames;
  GateDigiCollection *fHits;
  bool fDebug;
  bool fStoreAbsorbedEvent;

  int fNumberOfAbsorbedEvents;
  int fTotalNumberOfEntries;
};

#endif // GatePhaseSpaceActor_h
