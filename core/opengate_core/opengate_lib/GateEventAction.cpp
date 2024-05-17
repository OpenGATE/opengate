/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateEventAction.h"

GateEventAction::GateEventAction() : G4UserEventAction() {}

void GateEventAction::RegisterActor(GateVActor *actor) {
  if (actor->HasAction("BeginOfEventAction")) {
    fBeginOfEventAction_actors.push_back(actor);
  }
  if (actor->HasAction("EndOfEventAction")) {
    fEndOfEventAction_actors.push_back(actor);
  }
}

void GateEventAction::BeginOfEventAction(const G4Event *event) {
  for (auto actor : fBeginOfEventAction_actors) {
    actor->BeginOfEventAction(event);
  }
}

void GateEventAction::EndOfEventAction(const G4Event *event) {
  for (auto actor : fEndOfEventAction_actors) {
    actor->EndOfEventAction(event);
  }
}
