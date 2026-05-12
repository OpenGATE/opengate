/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateTLETrackModeAttribute.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "digitizer/GateDigiAttributeManager.h"

#include "G4AutoLock.hh"
#include "G4Electron.hh"

#include <limits>

G4Mutex TLETrackModeAttributeInitMutex = G4MUTEX_INITIALIZER;

GateTLETrackModeAttribute::GateTLETrackModeAttribute(py::dict &user_info)
    : GateVAuxiliaryAttribute(user_info) {
  fDigiAttributeType = 'I';
  fActions.insert("PreUserTrackingAction");
  fActions.insert("SteppingAction");
  fEnergyMin = 0.0;
  fTLEThreshold = 0.0;
}

void GateTLETrackModeAttribute::InitializeUserInfo(py::dict &user_info) {
  GateVAuxiliaryAttribute::InitializeUserInfo(user_info);
  fStrTLEThresholdType = DictGetStr(user_info, "tle_threshold_type");
  fTLEThreshold = DictGetDouble(user_info, "tle_threshold");
  fEnergyMin = DictGetDouble(user_info, "energy_min");
  fDatabase = DictGetStr(user_info, "database");
  if (fStrTLEThresholdType == "max range") {
    fTLEThresholdType = 0;
  } else if (fStrTLEThresholdType == "average range") {
    fTLEThresholdType = 1;
  } else if (fStrTLEThresholdType == "energy") {
    fTLEThresholdType = 2;
  } else if (fStrTLEThresholdType == "None") {
    fTLEThresholdType = 3;
  } else {
    Fatal("Invalid tle_threshold_type for attribute '" + fName + "'.");
  }
}

void GateTLETrackModeAttribute::InitializeCpp() {
  GateVAuxiliaryAttribute::InitializeCpp();

  // Optional DigiAttribute exposure so the current TLE mode can be written by
  // ROOT-backed actors or consumed by generic filters using the same name.
  auto fill = [=](GateVDigiAttribute *att, G4Step *step) {
    att->FillIValue(GetIValue(step));
  };
  auto *manager = GateDigiAttributeManager::GetInstance();
  manager->DefineDigiAttribute(fName, fDigiAttributeType, fill);
}

void GateTLETrackModeAttribute::EnsureRuntimeInitialized() {
  if (fEmCalc != nullptr && fMaterialMuHandler != nullptr)
    return;

  // The TLE policy depends on EM tables and mu data that are safest to obtain
  // lazily once tracking has started.
  G4AutoLock mutex(&TLETrackModeAttributeInitMutex);
  if (fEmCalc == nullptr) {
    fEmCalc = new G4EmCalculator;
  }
  if (fMaterialMuHandler == nullptr) {
    G4double ekinMax = 0.0;
    if ((fTLEThresholdType == 0) || (fTLEThresholdType == 1)) {
      if (fTLEThreshold != std::numeric_limits<double>::infinity()) {
        ekinMax = FindEkinMaxForTLE();
      } else {
        ekinMax = 50 * CLHEP::MeV;
      }
    } else if (fTLEThresholdType == 2) {
      ekinMax = fTLEThreshold;
    }
    if (fTLEThresholdType <= 2) {
      fMaterialMuHandler =
          GateMaterialMuHandler::GetInstance(fDatabase, ekinMax);
    } else {
      fMaterialMuHandler =
          GateMaterialMuHandler::GetInstance(fDatabase, 5 * CLHEP::MeV);
    }
  }
}

G4double GateTLETrackModeAttribute::FindEkinMaxForTLE() {
  G4MaterialTable *matTable = G4Material::GetMaterialTable();
  G4int nbOfMaterials = G4Material::GetNumberOfMaterials();
  G4double ekinMax = 0;
  for (G4int i = 0; i < nbOfMaterials; i++) {
    G4Material *currentMat = (*matTable)[i];
    G4double ekin =
        fEmCalc->GetKinEnergy(fTLEThreshold, G4Electron::Definition(), currentMat);
    if (i == 0 || ekin > ekinMax) {
      ekinMax = ekin;
    }
  }
  return ekinMax;
}

void GateTLETrackModeAttribute::InitializeCSDAForNewGamma(bool isFirstStep,
                                                          const G4Step *step) {
  if (!isFirstStep)
    return;
  if (step->GetTrack()->GetDefinition()->GetParticleName() != "gamma")
    return;
  auto &l = fThreadLocalData.Get();
  const auto *pre_step = step->GetPreStepPoint();
  const auto energy = pre_step->GetKineticEnergy();
  const auto *currentMat = pre_step->GetMaterial();
  l.fCsda = fEmCalc->GetCSDARange(energy, G4Electron::Definition(), currentMat);
  l.fPreviousMatName = currentMat->GetName();
  l.fPreviousEnergy = energy;
}

bool GateTLETrackModeAttribute::ComputeTLEConditionForGamma(
    const G4Step *step) {
  const auto *pre_step = step->GetPreStepPoint();
  const auto *currentMat = pre_step->GetMaterial();
  const auto energy = pre_step->GetKineticEnergy();
  auto &l = fThreadLocalData.Get();

  if (fTLEThresholdType <= 1)
    InitializeCSDAForNewGamma(l.fIsFirstStep, step);

  if ((fTLEThresholdType == 0) || (fTLEThresholdType == 1)) {
    auto sec_ekin = energy;
    G4double mu_en_over_rho = 0.0;
    if (fTLEThresholdType == 1) {
      mu_en_over_rho = fMaterialMuHandler->GetMuEnOverRho(
          pre_step->GetMaterialCutsCouple(), energy);
    }

    if ((energy != l.fPreviousEnergy) ||
        ((pre_step->GetStepStatus() == 1) &&
         (currentMat->GetName() != l.fPreviousMatName))) {
      if (fTLEThresholdType == 1) {
        const auto mu_over_rho = fMaterialMuHandler->GetMuOverRho(
            pre_step->GetMaterialCutsCouple(), energy);
        sec_ekin = energy * mu_en_over_rho / mu_over_rho;
      }
      l.fCsda = fEmCalc->GetCSDARange(sec_ekin, G4Electron::Definition(),
                                      currentMat);
      l.fPreviousMatName = currentMat->GetName();
      l.fPreviousEnergy = energy;
    }
    return l.fCsda / CLHEP::mm <= fTLEThreshold;
  }

  if (fTLEThresholdType == 2) {
    return energy / CLHEP::MeV <= fTLEThreshold / CLHEP::MeV;
  }

  return true;
}

void GateTLETrackModeAttribute::PreUserTrackingAction(const G4Track *track) {
  auto &l = fThreadLocalData.Get();
  l.fIsFirstStep = true;

  // If no mode was propagated from a parent track, the default is the
  // conventional scoring path.
  const auto existing_mode =
      GetAuxiliaryTrackInformationStoredValue<GateIntAuxiliaryTrackInformation, int>(
          track, kConventional);
  if (existing_mode == kConventional) {
    SetAuxiliaryTrackInformationStoredValue<GateIntAuxiliaryTrackInformation, int>(
        track, kConventional);
  }
}

void GateTLETrackModeAttribute::SteppingAction(const G4Step *step) {
  EnsureRuntimeInitialized();
  auto &l = fThreadLocalData.Get();
  const auto *track = step->GetTrack();
  const auto particle_name = track->GetDefinition()->GetParticleName();

  auto current_mode =
      GetAuxiliaryTrackInformationStoredValue<GateIntAuxiliaryTrackInformation, int>(
          step, kConventional);

  if (particle_name == "gamma") {
    const auto tle_condition =
        (fTLEThresholdType <= 2) ? ComputeTLEConditionForGamma(step) : true;
    current_mode = tle_condition ? kTLEGamma : kConventional;
    SetAuxiliaryTrackInformationStoredValue<GateIntAuxiliaryTrackInformation, int>(
        track, current_mode);
    // A gamma in TLE mode suppresses explicit deposition by the secondaries it
    // creates; otherwise secondaries follow the conventional path.
    const int propagated_mode =
        tle_condition ? kSuppressedSecondary : kConventional;
    SetAuxiliaryTrackInformationStoredValueOnSecondariesInCurrentStep<
        GateIntAuxiliaryTrackInformation, int>(step, propagated_mode);
  } else {
    // Non-gamma tracks keep their inherited mode and propagate that same mode
    // further down the genealogy.
    SetAuxiliaryTrackInformationStoredValue<GateIntAuxiliaryTrackInformation, int>(
        track, current_mode);
    SetAuxiliaryTrackInformationStoredValueOnSecondariesInCurrentStep<
        GateIntAuxiliaryTrackInformation, int>(step, current_mode);
  }

  l.fIsFirstStep = false;
}

int GateTLETrackModeAttribute::GetIValue(const G4Step *step) const {
  return GetAuxiliaryTrackInformationStoredValue<GateIntAuxiliaryTrackInformation,
                                                 int>(step, kConventional);
}
