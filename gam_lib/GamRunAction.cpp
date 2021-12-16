/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamRunAction.h"


GamRunAction::GamRunAction() : G4UserRunAction() {

}

void GamRunAction::RegisterActor(GamVActor *actor) {
    auto actions = actor->fActions;
    auto beg = std::find(actions.begin(), actions.end(), "BeginOfRunAction");
    if (beg != actions.end()) {
        fBeginOfRunAction_actors.push_back(actor);
    }
    auto end = std::find(actions.begin(), actions.end(), "EndOfRunAction");
    if (end != actions.end()) {
        fEndOfRunAction_actors.push_back(actor);
    }
}

void GamRunAction::BeginOfRunAction(const G4Run *Run) {

    // FIXME if first run call StartSimulationWorker ?

    for (auto actor : fBeginOfRunAction_actors) {
        actor->BeginOfRunAction(Run);
    }
}

void GamRunAction::EndOfRunAction(const G4Run *Run) {
    for (auto actor :fEndOfRunAction_actors) {
        actor->EndOfRunAction(Run);
    }
}
