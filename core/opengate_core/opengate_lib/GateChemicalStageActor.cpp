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
#include "G4EventManager.hh"
#include "G4Molecule.hh"
#include "G4MoleculeCounter.hh"
#include "G4MoleculeCounterManager.hh"
#include "G4RunManager.hh"
#include "G4Scheduler.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4Track.hh"

#include <algorithm>
#include <cmath>
#include <sstream>

namespace {
G4Mutex GateChemicalStageActorMutex = G4MUTEX_INITIALIZER;
}

GateChemicalStageActor::GateChemicalStageActor(py::dict &user_info)
    : GateVChemistryActor(user_info, true) {}

void GateChemicalStageActor::InitializeUserInfo(py::dict &user_info) {
  GateVChemistryActor::InitializeUserInfo(user_info);
  fTrackOnlyPrimary = DictGetBool(user_info, "track_only_primary");
  fPrimaryPDGCode = DictGetInt(user_info, "primary_pdg_code");
  fELossMin = DictGetDouble(user_info, "energy_loss_min");
  fELossMax = DictGetDouble(user_info, "energy_loss_max");
  fKineticEMin = DictGetDouble(user_info, "min_kinetic_energy");
  fLETCutoff = DictGetDouble(user_info, "let_cutoff");
  fTimesToRecord = DictGetVecDouble(user_info, "times_to_record");
  fNumberOfTimeBins = DictGetInt(user_info, "number_of_time_bins");
  std::sort(fTimesToRecord.begin(), fTimesToRecord.end());
  fTimesToRecord.erase(
      std::unique(fTimesToRecord.begin(), fTimesToRecord.end()),
      fTimesToRecord.end());
}

void GateChemicalStageActor::StartSimulationAction() {
  G4AutoLock lock(&GateChemicalStageActorMutex);
  fAccumulatedELoss = 0.0;
  fAccumulatedEdep = 0.0;
  fAccumulatedLET = 0.0;
  fAccumulatedLET2 = 0.0;
  fNbKilledParticles = 0;
  fNbAbortedEvents = 0;
  fNbChemistryStarts = 0;
  fNbChemistryStages = 0;
  fNbPreTimeStepCalls = 0;
  fNbPostTimeStepCalls = 0;
  fNbReactions = 0;
  fNbRecordedEvents = 0;
  fSpeciesInfoPerTime.clear();
  fReactionCounts.clear();
}

void GateChemicalStageActor::BeginOfEventAction(const G4Event * /*event*/) {
  fEventELoss = 0.0;
  fEventEdep = 0.0;
  fEventStepLength = 0.0;
  fEventRestrictedLET = 0.0;
  fLETTrackID = 1;
}

void GateChemicalStageActor::EndOfEventAction(const G4Event *event) {
  if (event->IsAborted()) {
    fLETTrackID = 1;
    fEventRestrictedLET = 0.0;
    fEventStepLength = 0.0;
    fEventEdep = 0.0;
    return;
  }

  if (fEventStepLength > 0.0) {
    fEventRestrictedLET = fEventEdep / fEventStepLength;
    G4AutoLock lock(&GateChemicalStageActorMutex);
    fAccumulatedLET += fEventRestrictedLET;
    fAccumulatedLET2 += fEventRestrictedLET * fEventRestrictedLET;
  }

  fLETTrackID = 1;
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
  const auto *preStepPoint = step->GetPreStepPoint();
  const auto *postStepPoint = step->GetPostStepPoint();

  if (!ShouldApplyPrimaryLogic(track)) {
    // chem6 LET scorer continues to follow charge-changed descendants
    if (track->GetTrackID() != 1 &&
        track->GetParticleDefinition()->GetPDGEncoding() != fPrimaryPDGCode &&
        track->GetCreatorProcess() != nullptr) {
      const auto subType = track->GetCreatorProcess()->GetProcessSubType();
      if (subType == 56 || subType == 57) {
        fLETTrackID = track->GetTrackID();
      }
    }
  } else {
    fLETTrackID = track->GetTrackID();
  }

  if (track->GetTrackID() == fLETTrackID) {
    fEventStepLength += step->GetStepLength() / um;
    fEventEdep += step->GetTotalEnergyDeposit() / keV;

    if (postStepPoint->GetProcessDefinedStep() != nullptr) {
      const auto subType = postStepPoint->GetProcessDefinedStep()->GetProcessSubType();
      if (subType != 56 && subType != 57) {
        const auto *secondary = step->GetSecondaryInCurrentStep();
        if (secondary != nullptr) {
          for (const auto *s : *secondary) {
            if (s->GetKineticEnergy() < fLETCutoff) {
              fEventEdep += s->GetKineticEnergy() / keV;
            }
          }
        }
      }
    }
  }

  if (!ShouldApplyPrimaryLogic(track)) {
    return;
  }

  const auto kineticE = postStepPoint->GetKineticEnergy();
  const auto eLoss = preStepPoint->GetKineticEnergy() - kineticE;

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

  if ((fELossMin >= 0.0 && fEventELoss >= fELossMin) ||
      kineticE <= fKineticEMin) {
    track->SetTrackStatus(fStopAndKill);
    G4AutoLock lock(&GateChemicalStageActorMutex);
    fNbKilledParticles++;
  }
}

void GateChemicalStageActor::NewStage() {
  G4AutoLock lock(&GateChemicalStageActorMutex);
  fNbChemistryStages++;
}

void GateChemicalStageActor::StartProcessing() {
  ConfigureTimesToRecordIfNeeded();
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

void GateChemicalStageActor::UserReactionAction(
    const G4Track &trackA, const G4Track &trackB,
    const std::vector<G4Track *> *products) {
  const auto signature = GetReactionSignature(trackA, trackB, products);
  G4AutoLock lock(&GateChemicalStageActorMutex);
  fNbReactions++;
  fReactionCounts[signature]++;
}

void GateChemicalStageActor::EndProcessing() {
  RecordSpeciesAtEndOfChemicalStage();
}

double GateChemicalStageActor::GetMeanRestrictedLET() const {
  if (fNbRecordedEvents == 0) {
    return 0.0;
  }
  return fAccumulatedLET / static_cast<double>(fNbRecordedEvents);
}

double GateChemicalStageActor::GetStdRestrictedLET() const {
  if (fNbRecordedEvents == 0) {
    return 0.0;
  }
  const auto mean = GetMeanRestrictedLET();
  const auto variance =
      (fAccumulatedLET2 / static_cast<double>(fNbRecordedEvents)) - mean * mean;
  return variance > 0.0 ? std::sqrt(variance) : 0.0;
}

py::dict GateChemicalStageActor::GetSpeciesInfo() const {
  py::dict speciesInfo;
  for (const auto &[time, speciesMap] : fSpeciesInfoPerTime) {
    py::dict speciesAtTime;
    for (const auto &[speciesName, info] : speciesMap) {
      py::dict speciesEntry;
      speciesEntry["number"] = info.number;
      speciesEntry["sum_g"] = info.sumG;
      speciesEntry["sum_g2"] = info.sumG2;
      speciesAtTime[py::str(speciesName)] = speciesEntry;
    }
    speciesInfo[py::float_(time)] = speciesAtTime;
  }
  return speciesInfo;
}

py::dict GateChemicalStageActor::GetReactionCounts() const {
  py::dict reactionCounts;
  for (const auto &[signature, count] : fReactionCounts) {
    reactionCounts[py::str(signature)] = count;
  }
  return reactionCounts;
}

py::list GateChemicalStageActor::GetRecordedTimes() const {
  py::list recordedTimes;
  for (const auto time : fTimesToRecord) {
    recordedTimes.append(time);
  }
  return recordedTimes;
}

void GateChemicalStageActor::ConfigureTimesToRecordIfNeeded() {
  if (!fTimesToRecord.empty() || fNumberOfTimeBins <= 0) {
    return;
  }

  const auto endTime = G4Scheduler::Instance()->GetEndTime() - 1.0 * ps;
  constexpr auto timeMin = 1.0 * ps;
  if (endTime <= timeMin) {
    fTimesToRecord.push_back(endTime > 0.0 ? endTime : timeMin);
    return;
  }

  if (fNumberOfTimeBins == 1) {
    fTimesToRecord.push_back(endTime);
    return;
  }

  const auto timeLogMin = std::log10(timeMin);
  const auto timeLogMax = std::log10(endTime);
  for (auto i = 0; i < fNumberOfTimeBins; i++) {
    const auto time =
        std::pow(10.0, timeLogMin +
                           i * (timeLogMax - timeLogMin) /
                               static_cast<double>(fNumberOfTimeBins - 1));
    fTimesToRecord.push_back(time);
  }
}

void GateChemicalStageActor::RecordSpeciesAtEndOfChemicalStage() {
  const auto *currentEvent =
      G4EventManager::GetEventManager()->GetConstCurrentEvent();
  if (currentEvent == nullptr || currentEvent->IsAborted()) {
    return;
  }

  const auto *counter =
      fMoleculeCounterId >= 0
          ? G4MoleculeCounterManager::Instance()->GetMoleculeCounter<G4MoleculeCounter>(
                fMoleculeCounterId)
          : nullptr;
  if (counter == nullptr) {
    return;
  }

  const auto indices = counter->GetMapIndices();

  {
    G4AutoLock lock(&GateChemicalStageActorMutex);
    fNbRecordedEvents++;
    fAccumulatedEdep += fEventEdep;
  }

  if (indices.empty()) {
    return;
  }

  for (const auto &idx : indices) {
    const auto *molecule = idx.Molecule;
    if (molecule == nullptr) {
      continue;
    }
    const auto speciesName = molecule->GetName();
    for (const auto time : fTimesToRecord) {
      const auto nMolecules = counter->GetNbMoleculesAtTime(idx, time);
      G4AutoLock lock(&GateChemicalStageActorMutex);
      auto &entry = fSpeciesInfoPerTime[time][speciesName];
      entry.number += nMolecules;
      if (fEventEdep > 0.0) {
        const auto gValue = (nMolecules / (fEventEdep * keV / eV)) * 100.0;
        entry.sumG += gValue;
        entry.sumG2 += gValue * gValue;
      }
    }
  }
}

std::string GateChemicalStageActor::GetReactionSignature(
    const G4Track &trackA, const G4Track &trackB,
    const std::vector<G4Track *> *products) const {
  std::ostringstream oss;
  const auto *molA = GetMolecule(trackA);
  const auto *molB = GetMolecule(trackB);
  oss << (molA != nullptr ? molA->GetName() : "unknownA");
  oss << " + ";
  oss << (molB != nullptr ? molB->GetName() : "unknownB");
  oss << " -> ";

  if (products == nullptr || products->empty()) {
    oss << "none";
    return oss.str();
  }

  bool first = true;
  for (const auto *product : *products) {
    if (!first) {
      oss << " + ";
    }
    first = false;
    if (product == nullptr) {
      oss << "null";
      continue;
    }
    const auto *mol = GetMolecule(product);
    oss << (mol != nullptr ? mol->GetName() : "unknown");
  }
  return oss.str();
}
