/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateRunAction.h"
#include "GateHelpers.h"
#include "GateUniqueVolumeIDManager.h"

GateRunAction::GateRunAction(GateSourceManager *sm) : G4UserRunAction() {
  fSourceManager = sm;
}

void GateRunAction::RegisterActor(GateVActor *actor) {
  if (actor->HasAction("BeginOfRunAction")) {
    fBeginOfRunAction_actors.push_back(actor);
  }
  if (actor->HasAction("EndOfRunAction")) {
    fEndOfRunAction_actors.push_back(actor);
  }
  // FIXME rename EndOfLastRun ?
  if (actor->HasAction("EndOfSimulationWorkerAction")) {
    fEndOfSimulationWorkerAction_actors.push_back(actor);
  }
}

void GateRunAction::BeginOfRunAction(const G4Run *run) {
  // The map should be reset each run because of the motion can change the
  // touchable properties
  GateUniqueVolumeIDManager::Clear();
  for (const auto actor : fBeginOfRunAction_actors) {
    actor->BeginOfRunAction(run);
  }
}

void GateRunAction::EndOfRunAction(const G4Run *run) {
  for (const auto actor : fEndOfRunAction_actors) {
    actor->EndOfRunAction(run);
  }
  // If the simulation is about to end, we call the callback function for all
  // actors
  if (fSourceManager->IsEndOfSimulationForWorker()) {
    for (const auto actor : fEndOfSimulationWorkerAction_actors) {
      actor->EndOfSimulationWorkerAction(run);
    }
  }
}
