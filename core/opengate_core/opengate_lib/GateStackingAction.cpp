/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateStackingAction.h"
#include "G4DNAChemistryManager.hh"
#include "G4StackManager.hh"

GateStackingAction::GateStackingAction() : G4UserStackingAction() {
  fChemistryIsActive = false;
}

void GateStackingAction::RegisterActor(GateVActor *actor,
                                       bool is_chemistry_actor) {
  if (!actor->HasAction("NewStage")) {
    return;
  }
  if (is_chemistry_actor) {
    fChemistryStageActors.push_back(actor);
  } else {
    fNonChemistryStageActors.push_back(actor);
  }
}

void GateStackingAction::NewStage() {
  for (auto actor : fNonChemistryStageActors) {
    actor->NewStage();
  }
  for (auto actor : fChemistryStageActors) {
    actor->NewStage();
  }

  if (fChemistryIsActive && stackManager != nullptr &&
      stackManager->GetNTotalTrack() == 0) {
    G4DNAChemistryManager::Instance()->Run();
  }
}
