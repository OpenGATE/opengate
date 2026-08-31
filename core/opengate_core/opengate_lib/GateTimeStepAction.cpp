/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateTimeStepAction.h"

GateTimeStepAction::GateTimeStepAction() : G4UserTimeStepAction() {}

void GateTimeStepAction::RegisterActor(GateVChemistryActor *actor) {
  if (actor->HasAction("StartChemistryProcessing")) {
    fStartChemistryProcessingActors.push_back(actor);
  }
  if (actor->HasAction("NewStage")) {
    fNewStageActors.push_back(actor);
  }
  if (actor->HasAction("PreChemistryTimeStepAction")) {
    fPreChemistryTimeStepActors.push_back(actor);
  }
  if (actor->HasAction("PostChemistryTimeStepAction")) {
    fPostChemistryTimeStepActors.push_back(actor);
  }
  if (actor->HasAction("ChemistryReactionAction")) {
    fChemistryReactionActors.push_back(actor);
  }
  if (actor->HasAction("EndChemistryProcessing")) {
    fEndChemistryProcessingActors.push_back(actor);
  }
}

void GateTimeStepAction::StartProcessing() {
  for (auto actor : fStartChemistryProcessingActors) {
    actor->StartChemistryProcessing();
  }
}

void GateTimeStepAction::NewStage() {
  for (auto actor : fNewStageActors) {
    actor->NewStage();
  }
}

void GateTimeStepAction::UserPreTimeStepAction() {
  for (auto actor : fPreChemistryTimeStepActors) {
    actor->PreChemistryTimeStepAction();
  }
}

void GateTimeStepAction::UserPostTimeStepAction() {
  for (auto actor : fPostChemistryTimeStepActors) {
    actor->PostChemistryTimeStepAction();
  }
}

void GateTimeStepAction::UserReactionAction(
    const G4Track &trackA, const G4Track &trackB,
    const std::vector<G4Track *> *products) {
  for (auto actor : fChemistryReactionActors) {
    actor->ChemistryReactionAction(trackA, trackB, products);
  }
}

void GateTimeStepAction::EndProcessing() {
  for (auto actor : fEndChemistryProcessingActors) {
    actor->EndChemistryProcessing();
  }
}
