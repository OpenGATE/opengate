/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateEventAction.h"
#include <G4MoleculeCounterManager.hh>

GateEventAction::GateEventAction() : G4UserEventAction() {
  fChemistryIsActive = false;
}

void GateEventAction::RegisterActor(GateVActor *actor) {
  if (actor->HasAction("BeginOfEventAction")) {
    fBeginOfEventAction_actors.push_back(actor);
  }
  if (actor->HasAction("EndOfEventAction")) {
    fEndOfEventAction_actors.push_back(actor);
  }
}

void GateEventAction::BeginOfEventAction(const G4Event *event) {
  if (fChemistryIsActive) {
    // Chemistry scoring may instantiate the counter manager lazily. Once
    // chemistry is known to be active for the simulation, ensure the event
    // lifecycle reaches the live manager instance used by counters.
    G4MoleculeCounterManager::Instance()->BeginOfEventAction(event);
  }
  for (auto actor : fBeginOfEventAction_actors) {
    actor->BeginOfEventAction(event);
  }
}

void GateEventAction::EndOfEventAction(const G4Event *event) {
  for (auto actor : fEndOfEventAction_actors) {
    actor->EndOfEventAction(event);
  }
  if (fChemistryIsActive) {
    G4MoleculeCounterManager::Instance()->EndOfEventAction(event);
  }
}
