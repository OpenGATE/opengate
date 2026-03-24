/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateTimeStepAction.h"

GateTimeStepAction::GateTimeStepAction() : G4UserTimeStepAction() {}

void GateTimeStepAction::RegisterActor(GateVChemistryActor *actor) {
  if (actor->HasAction("StartProcessing")) {
    fStartProcessingActors.push_back(actor);
  }
  if (actor->HasAction("NewStage")) {
    fNewStageActors.push_back(actor);
  }
  if (actor->HasAction("UserPreTimeStepAction")) {
    fPreTimeStepActors.push_back(actor);
  }
  if (actor->HasAction("UserPostTimeStepAction")) {
    fPostTimeStepActors.push_back(actor);
  }
  if (actor->HasAction("UserReactionAction")) {
    fReactionActors.push_back(actor);
  }
  if (actor->HasAction("EndProcessing")) {
    fEndProcessingActors.push_back(actor);
  }
}

void GateTimeStepAction::StartProcessing() {
  for (auto actor : fStartProcessingActors) {
    actor->StartProcessing();
  }
}

void GateTimeStepAction::NewStage() {
  for (auto actor : fNewStageActors) {
    actor->NewStage();
  }
}

void GateTimeStepAction::UserPreTimeStepAction() {
  for (auto actor : fPreTimeStepActors) {
    actor->UserPreTimeStepAction();
  }
}

void GateTimeStepAction::UserPostTimeStepAction() {
  for (auto actor : fPostTimeStepActors) {
    actor->UserPostTimeStepAction();
  }
}

void GateTimeStepAction::UserReactionAction(
    const G4Track &trackA, const G4Track &trackB,
    const std::vector<G4Track *> *products) {
  for (auto actor : fReactionActors) {
    actor->UserReactionAction(trackA, trackB, products);
  }
}

void GateTimeStepAction::EndProcessing() {
  for (auto actor : fEndProcessingActors) {
    actor->EndProcessing();
  }
}
