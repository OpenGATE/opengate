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
    std::cout << "GamEventAction::RegisterActor " << std::endl;
    auto actions = actor->actions;
    auto beg = std::find(actions.begin(), actions.end(), "BeginOfEventAction");
    if (beg != actions.end()) {
        m_BeginOfEventAction_actors.push_back(actor);
    }
    auto end = std::find(actions.begin(), actions.end(), "EndOfEventAction");
    if (end != actions.end()) {
        m_EndOfEventAction_actors.push_back(actor);
    }
}

void GamEventAction::BeginOfEventAction(const G4Event *event) {
    for (auto actor : m_BeginOfEventAction_actors) {
        actor->BeginOfEventAction(event);
    }
}

void GamEventAction::EndOfEventAction(const G4Event *event) {
    for (auto actor :m_EndOfEventAction_actors) {
        actor->EndOfEventAction(event);
    }
}
