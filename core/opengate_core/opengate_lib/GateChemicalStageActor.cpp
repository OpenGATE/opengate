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
  for (auto &[counterName, trackedReactions] : fConfiguredReactionCounters) {
    for (auto &trackedReaction : trackedReactions) {
      trackedReaction.Reset();
    }
  }
  for (auto &[counterName, trackedSpecies] : fConfiguredSpeciesCounters) {
    for (auto &trackedSpeciesRecord : trackedSpecies) {
      trackedSpeciesRecord.Reset();
    }
  }
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

bool GateChemicalStageActor::ShouldApplyPrimaryLogic(
    const G4Track *track) const {
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
      const auto subType =
          postStepPoint->GetProcessDefinedStep()->GetProcessSubType();
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

void GateChemicalStageActor::StartChemistryTracking(G4Track *track) {
  if (track == nullptr) {
    return;
  }
  const auto runtimeName = ResolveRuntimeMoleculeName(*track);
  const auto trackTime = track->GetGlobalTime();
  G4AutoLock lock(&GateChemicalStageActorMutex);
  for (auto &[counterName, trackedSpecies] : fConfiguredSpeciesCounters) {
    for (auto &trackedSpeciesRecord : trackedSpecies) {
      if (trackedSpeciesRecord.runtimeName != runtimeName) {
        continue;
      }
      trackedSpeciesRecord.totalCount++;
      if (trackedSpeciesRecord.recordTimeSeries) {
        if (!trackedSpeciesRecord.times.empty() &&
            trackedSpeciesRecord.times.back() == trackTime) {
          trackedSpeciesRecord.counts.back() = trackedSpeciesRecord.totalCount;
        } else {
          trackedSpeciesRecord.times.push_back(trackTime);
          trackedSpeciesRecord.counts.push_back(trackedSpeciesRecord.totalCount);
        }
      } else {
        trackedSpeciesRecord.times.back() = trackTime;
        trackedSpeciesRecord.counts.back() = trackedSpeciesRecord.totalCount;
      }
    }
  }
}

void GateChemicalStageActor::StartChemistryProcessing() {
  ConfigureTimesToRecordIfNeeded();
  G4AutoLock lock(&GateChemicalStageActorMutex);
  fNbChemistryStarts++;
}

void GateChemicalStageActor::PreChemistryTimeStepAction() {
  G4AutoLock lock(&GateChemicalStageActorMutex);
  fNbPreTimeStepCalls++;
}

void GateChemicalStageActor::PostChemistryTimeStepAction() {
  G4AutoLock lock(&GateChemicalStageActorMutex);
  fNbPostTimeStepCalls++;
}

void GateChemicalStageActor::ChemistryReactionAction(
    const G4Track &trackA, const G4Track &trackB,
    const std::vector<G4Track *> *products) {
  const auto reactants = CanonicalizeReactants(ResolveRuntimeMoleculeName(trackA),
                                               ResolveRuntimeMoleculeName(trackB));
  std::vector<std::string> productNames;
  if (products != nullptr) {
    productNames.reserve(products->size());
    for (const auto *product : *products) {
      if (product != nullptr) {
        productNames.push_back(ResolveRuntimeMoleculeName(*product));
      }
    }
  }
  const auto canonicalProducts = CanonicalizeProducts(productNames);
  const auto reactionTime = std::min(trackA.GetGlobalTime(), trackB.GetGlobalTime());

  G4AutoLock lock(&GateChemicalStageActorMutex);
  fNbReactions++;
  for (auto &[counterName, trackedReactions] : fConfiguredReactionCounters) {
    for (auto &trackedReaction : trackedReactions) {
      if (trackedReaction.reactants != reactants ||
          trackedReaction.products != canonicalProducts) {
        continue;
      }
      trackedReaction.totalCount++;
      if (trackedReaction.recordTimeSeries) {
        if (!trackedReaction.times.empty() &&
            trackedReaction.times.back() == reactionTime) {
          trackedReaction.counts.back() = trackedReaction.totalCount;
        } else {
          trackedReaction.times.push_back(reactionTime);
          trackedReaction.counts.push_back(trackedReaction.totalCount);
        }
      } else {
        trackedReaction.times.back() = reactionTime;
        trackedReaction.counts.back() = trackedReaction.totalCount;
      }
    }
  }
}

void GateChemicalStageActor::EndChemistryProcessing() {
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

py::list GateChemicalStageActor::GetRecordedTimes() const {
  py::list recordedTimes;
  for (const auto time : fTimesToRecord) {
    recordedTimes.append(time);
  }
  return recordedTimes;
}

void GateChemicalStageActor::RegisterConfiguredReactionCounter(
    const std::string &counterName, const py::list &trackedReactions,
    bool recordTimeSeries) {
  std::vector<TrackedReactionRecord> records;
  records.reserve(trackedReactions.size());
  for (const auto &item : trackedReactions) {
    const auto reactionDict = py::cast<py::dict>(item);
    TrackedReactionRecord record;
    record.name = py::cast<std::string>(reactionDict["name"]);
    record.reactants = CanonicalizeReactants(
        py::cast<std::string>(reactionDict["reactant_a"]),
        py::cast<std::string>(reactionDict["reactant_b"]));
    record.products = CanonicalizeProducts(
        py::cast<std::vector<std::string>>(reactionDict["products"]));
    record.recordTimeSeries = recordTimeSeries;
    record.Reset();
    records.push_back(std::move(record));
  }
  G4AutoLock lock(&GateChemicalStageActorMutex);
  fConfiguredReactionCounters[counterName] = std::move(records);
}

py::dict GateChemicalStageActor::GetConfiguredReactionCounterResults(
    const std::string &counterName) const {
  py::dict results;
  auto it = fConfiguredReactionCounters.find(counterName);
  if (it == fConfiguredReactionCounters.end()) {
    return results;
  }
  for (const auto &trackedReaction : it->second) {
    py::dict entry;
    py::list times;
    py::list counts;
    for (const auto time : trackedReaction.times) {
      times.append(time);
    }
    for (const auto count : trackedReaction.counts) {
      counts.append(count);
    }
    entry["times"] = times;
    entry["counts"] = counts;
    results[py::str(trackedReaction.name)] = entry;
  }
  return results;
}

void GateChemicalStageActor::RegisterConfiguredSpeciesCounter(
    const std::string &counterName, const py::list &trackedSpecies,
    bool recordTimeSeries) {
  std::vector<TrackedSpeciesRecord> records;
  records.reserve(trackedSpecies.size());
  for (const auto &item : trackedSpecies) {
    const auto speciesDict = py::cast<py::dict>(item);
    TrackedSpeciesRecord record;
    record.name = py::cast<std::string>(speciesDict["name"]);
    record.runtimeName = py::cast<std::string>(speciesDict["runtime_name"]);
    record.recordTimeSeries = recordTimeSeries;
    record.Reset();
    records.push_back(std::move(record));
  }
  G4AutoLock lock(&GateChemicalStageActorMutex);
  fConfiguredSpeciesCounters[counterName] = std::move(records);
}

py::dict GateChemicalStageActor::GetConfiguredSpeciesCounterResults(
    const std::string &counterName) const {
  py::dict results;
  auto it = fConfiguredSpeciesCounters.find(counterName);
  if (it == fConfiguredSpeciesCounters.end()) {
    return results;
  }
  for (const auto &trackedSpecies : it->second) {
    py::dict entry;
    py::list times;
    py::list counts;
    for (const auto time : trackedSpecies.times) {
      times.append(time);
    }
    for (const auto count : trackedSpecies.counts) {
      counts.append(count);
    }
    entry["times"] = times;
    entry["counts"] = counts;
    results[py::str(trackedSpecies.name)] = entry;
  }
  return results;
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
    const auto time = std::pow(
        10.0, timeLogMin + i * (timeLogMax - timeLogMin) /
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
          ? G4MoleculeCounterManager::Instance()
                ->GetMoleculeCounter<G4MoleculeCounter>(fMoleculeCounterId)
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

std::array<std::string, 2> GateChemicalStageActor::CanonicalizeReactants(
    const std::string &reactantA, const std::string &reactantB) {
  std::array<std::string, 2> reactants{reactantA, reactantB};
  std::sort(reactants.begin(), reactants.end());
  return reactants;
}

std::vector<std::string> GateChemicalStageActor::CanonicalizeProducts(
    const std::vector<std::string> &products) {
  auto sortedProducts = products;
  std::sort(sortedProducts.begin(), sortedProducts.end());
  return sortedProducts;
}

std::string GateChemicalStageActor::ResolveRuntimeMoleculeName(
    const G4Track &track) {
  const auto *molecule = G4Molecule::GetMolecule(&track);
  if (molecule != nullptr) {
    const auto *configuration = molecule->GetMolecularConfiguration();
    if (configuration != nullptr) {
      return configuration->GetName();
    }
  }
  if (track.GetParticleDefinition() != nullptr) {
    return track.GetParticleDefinition()->GetParticleName();
  }
  return "";
}
