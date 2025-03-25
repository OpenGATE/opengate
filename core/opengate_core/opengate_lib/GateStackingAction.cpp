/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateStackingAction.h"

void GateStackingAction::RegisterActor(GateVActor *actor) {
  auto actions = actor->fActions;
  auto beg = std::find(std::begin(actions), std::end(actions), "NewStage");
  if (beg != actions.end()) {
    fNewStageActors.push_back(actor);
  }
}

void GateStackingAction::NewStage() {
  for (auto *actor : fNewStageActors) {
    actor->NewStage();
  }
}
