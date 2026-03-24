/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateChemicalStageActor.h"
#include "GateHelpersDict.h"

#include "G4AutoLock.hh"
#include "G4Event.hh"
#include "G4RunManager.hh"
#include "G4Step.hh"
#include "G4Track.hh"

namespace {
G4Mutex GateChemicalStageActorMutex = G4MUTEX_INITIALIZER;
}

GateChemicalStageActor::GateChemicalStageActor(py::dict &user_info)
    : GateVChemistryActor(user_info, true),
      fBoundingBoxSize(-1.0, -1.0, -1.0) {}

void GateChemicalStageActor::InitializeUserInfo(py::dict &user_info) {
  GateVChemistryActor::InitializeUserInfo(user_info);
  fTrackOnlyPrimary = DictGetBool(user_info, "track_only_primary");
  fPrimaryPDGCode = DictGetInt(user_info, "primary_pdg_code");
  fELossMin = DictGetDouble(user_info, "energy_loss_min");
  fELossMax = DictGetDouble(user_info, "energy_loss_max");
  fBoundingBoxSize = DictGetG4ThreeVector(user_info, "bounding_box_size");
  fUseBoundingBox = DictGetBool(user_info, "use_bounding_box");
}

void GateChemicalStageActor::StartSimulationAction() {
  G4AutoLock lock(&GateChemicalStageActorMutex);
  fAccumulatedELoss = 0.0;
  fNbKilledParticles = 0;
  fNbAbortedEvents = 0;
  fNbChemistryStarts = 0;
  fNbPreTimeStepCalls = 0;
  fNbPostTimeStepCalls = 0;
}

void GateChemicalStageActor::BeginOfEventAction(const G4Event * /*event*/) {
  fEventELoss = 0.0;
}

bool GateChemicalStageActor::ShouldApplyPrimaryLogic(const G4Track *track) const {
  if (!fTrackOnlyPrimary) {
    return true;
  }
  if (track->GetTrackID() != 1) {
    return false;
  }
  return track->GetParticleDefinition()->GetPDGEncoding() == fPrimaryPDGCode;
}

void GateChemicalStageActor::SteppingAction(G4Step *step) {
  auto *track = step->GetTrack();

  if (fUseBoundingBox) {
    const auto pos = step->GetPostStepPoint()->GetPosition();
    const bool outside =
        std::abs(pos.x()) > fBoundingBoxSize.x() / 2.0 ||
        std::abs(pos.y()) > fBoundingBoxSize.y() / 2.0 ||
        std::abs(pos.z()) > fBoundingBoxSize.z() / 2.0;
    if (outside) {
      track->SetTrackStatus(fStopAndKill);
      G4AutoLock lock(&GateChemicalStageActorMutex);
      fNbKilledParticles++;
      return;
    }
  }

  if (!ShouldApplyPrimaryLogic(track)) {
    return;
  }

  const auto kineticE = step->GetPostStepPoint()->GetKineticEnergy();
  const auto eLoss =
      step->GetPreStepPoint()->GetKineticEnergy() - kineticE;

  if (eLoss <= 0.0) {
    return;
  }

  fEventELoss += eLoss;
  {
    G4AutoLock lock(&GateChemicalStageActorMutex);
    fAccumulatedELoss += eLoss;
  }

  if (fELossMax >= 0.0 && fEventELoss > fELossMax) {
    G4RunManager::GetRunManager()->AbortEvent();
    G4AutoLock lock(&GateChemicalStageActorMutex);
    fNbAbortedEvents++;
    return;
  }

  if (fELossMin >= 0.0 && fEventELoss >= fELossMin) {
    track->SetTrackStatus(fStopAndKill);
    G4AutoLock lock(&GateChemicalStageActorMutex);
    fNbKilledParticles++;
  }
}

void GateChemicalStageActor::NewStage() {}

void GateChemicalStageActor::StartProcessing() {
  G4AutoLock lock(&GateChemicalStageActorMutex);
  fNbChemistryStarts++;
}

void GateChemicalStageActor::UserPreTimeStepAction() {
  G4AutoLock lock(&GateChemicalStageActorMutex);
  fNbPreTimeStepCalls++;
}

void GateChemicalStageActor::UserPostTimeStepAction() {
  G4AutoLock lock(&GateChemicalStageActorMutex);
  fNbPostTimeStepCalls++;
}

void GateChemicalStageActor::EndProcessing() {}
