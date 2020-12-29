/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamTrackingAction.h"


GamTrackingAction::GamTrackingAction() : G4UserTrackingAction() {

}

void GamTrackingAction::RegisterActor(GamVActor *actor) {
    auto actions = actor->actions;
    auto beg = std::find(actions.begin(), actions.end(), "PreUserTrackingAction");
    if (beg != actions.end()) {
        fPreUserTrackingActionActors.push_back(actor);
    }
    auto end = std::find(actions.begin(), actions.end(), "PostUserTrackingAction");
    if (end != actions.end()) {
        fPostUserTrackingActionActors.push_back(actor);
    }
}

void GamTrackingAction::PreUserTrackingAction(const G4Track *track) {
    for (auto actor : fPreUserTrackingActionActors) {
        actor->PreUserTrackingAction(track);
    }
}

void GamTrackingAction::PostUserTrackingAction(const G4Track *track) {
    for (auto actor :fPostUserTrackingActionActors) {
        actor->PostUserTrackingAction(track);
    }
}
