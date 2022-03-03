/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamRunAction.h"
#include "GamHelpers.h"

GamRunAction::GamRunAction(GamSourceManager *sm) : G4UserRunAction() {
    fSourceManager = sm;
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

    // FIXME rename EndOfLastRun
    auto send = std::find(actions.begin(), actions.end(), "EndOfSimulationWorkerAction");
    if (send != actions.end()) {
        fEndOfSimulationWorkerAction_actors.push_back(actor);
    }
}

void GamRunAction::BeginOfRunAction(const G4Run *run) {
    // FIXME if first run call StartSimulationWorker ?
    for (auto actor: fBeginOfRunAction_actors) {
        actor->BeginOfRunAction(run);
    }
}

void GamRunAction::EndOfRunAction(const G4Run *run) {
    for (auto actor: fEndOfRunAction_actors) {
        actor->EndOfRunAction(run);
    }
    // If the simulation is about to end, we call the callback function for all actors
    if (fSourceManager->IsEndOfSimulationForWorker()) {
        for (auto actor: fEndOfSimulationWorkerAction_actors) {
            actor->EndOfSimulationWorkerAction(run);
        }
    }
}
