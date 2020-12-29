/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamSteppingAction.h"


GamSteppingAction::GamSteppingAction() : G4UserSteppingAction() {

}

void GamSteppingAction::RegisterActor(GamVActor *actor) {
    auto actions = actor->actions;
    auto beg = std::find(actions.begin(), actions.end(), "UserSteppingAction");
    if (beg != actions.end()) {
        fUserSteppingActionActors.push_back(actor);
    }
}

void GamSteppingAction::UserSteppingAction(const G4Step *step) {
    /*
    for (auto actor : fUserSteppingActionActors) {
        actor->UserSteppingAction(step);
    }*/}
