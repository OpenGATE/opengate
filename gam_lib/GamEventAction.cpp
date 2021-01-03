/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamEventAction.h"


GamEventAction::GamEventAction() : G4UserEventAction() {

}

void GamEventAction::RegisterActor(GamVActor *actor) {
    auto actions = actor->actions;
    auto beg = std::find(actions.begin(), actions.end(), "BeginOfEventAction");
    if (beg != actions.end()) {
        fBeginOfEventAction_actors.push_back(actor);
    }
    auto end = std::find(actions.begin(), actions.end(), "EndOfEventAction");
    if (end != actions.end()) {
        fEndOfEventAction_actors.push_back(actor);
    }
}

void GamEventAction::BeginOfEventAction(const G4Event *event) {
    for (auto actor : fBeginOfEventAction_actors) {
        actor->BeginOfEventAction(event);
    }
}

void GamEventAction::EndOfEventAction(const G4Event *event) {
    for (auto actor :fEndOfEventAction_actors) {
        actor->EndOfEventAction(event);
    }
}
