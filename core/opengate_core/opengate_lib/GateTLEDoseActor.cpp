/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateTLEDoseActor.h"
#include "G4Electron.hh"
#include "G4EmCalculator.hh"
#include "G4Exception.hh"
#include "G4ParticleDefinition.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "G4Threading.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"
#include "GateMaterialMuHandler.h"
#include "GateUserTrackInformation.h"

#include <iostream>
#include <itkAddImageFilter.h>
#include <vector>

G4Mutex SetPixelTLEMutex = G4MUTEX_INITIALIZER;
G4Mutex SetEkinMaxMutex = G4MUTEX_INITIALIZER;

GateTLEDoseActor::GateTLEDoseActor(py::dict &user_info)
    : GateDoseActor(user_info) {
  fMultiThreadReady = true;
  fEnergyMin = 0;
  fTLEThreshold = 0;
}

void GateTLEDoseActor::InitializeUserInfo(py::dict &user_info) {
  GateDoseActor::InitializeUserInfo(user_info);
  fStrTLEThresholdType = py::cast<std::string>(user_info["tle_threshold_type"]);
  fTLEThreshold = py::cast<double>(user_info["tle_threshold"]);
  fEnergyMin = py::cast<double>(user_info["energy_min"]);
  fDatabase = py::cast<std::string>(user_info["database"]);
  if (fStrTLEThresholdType == "max range") {
    fTLEThresholdType = 0;
  } else if (fStrTLEThresholdType == "average range") {
    fTLEThresholdType = 1;
  } else if (fStrTLEThresholdType == "energy") {
    fTLEThresholdType = 2;
  } else if (fStrTLEThresholdType == "None") {
    fTLEThresholdType = 3;
  } else {
    G4ExceptionDescription ed;
    ed << "You did not define a correct threshold type" << G4endl;
    G4Exception("GateTLEDoseActor::InitializeUserInfo", "TLE.LV1",
                FatalException, ed);
  }
}

void GateTLEDoseActor::SetTLETrackInformationOnSecondaries(G4Step *step,
                                                           G4bool info,
                                                           G4int nbSec) {
  if (nbSec > 0) {
    for (auto i = 0; i < nbSec; i++) {
      GateUserTrackInformation *trackInfo = nullptr;
      auto *secs = step->GetfSecondary();
      auto *sec = (*secs)[secs->size() - i - 1];
      if (sec->GetUserInformation() == 0) {
        trackInfo = new GateUserTrackInformation();
      } else {
        trackInfo =
            dynamic_cast<GateUserTrackInformation *>(sec->GetUserInformation());
      }
      trackInfo->SetGateTrackInformation(this, info);
      sec->SetUserInformation(trackInfo);
    }
  }
}

G4double GateTLEDoseActor::FindEkinMaxForTLE() {
  G4MaterialTable *matTable = G4Material::GetMaterialTable();
  G4int nbOfMaterials = G4Material::GetNumberOfMaterials();
  G4double ekinMax = 0;
  for (G4int i = 0; i < nbOfMaterials; i++) {
    G4Material *currentMat = (*matTable)[i];
    G4double ekin = fEmCalc->GetKinEnergy(fTLEThreshold,
                                          G4Electron::Definition(), currentMat);
    if (i == 0) {
      ekinMax = ekin;
    }
    if (ekin > ekinMax) {
      ekinMax = ekin;
    }
  }
  return ekinMax;
}

void GateTLEDoseActor::InitializeCSDAForNewGamma(G4bool isFirstStep,
                                                 G4Step *step) {
  if ((isFirstStep) &&
      (step->GetTrack()->GetDefinition()->GetParticleName() == "gamma")) {
    auto &l = fThreadLocalData.Get();
    G4StepPoint *pre_step = step->GetPreStepPoint();
    G4double energy = pre_step->GetKineticEnergy();
    const G4Material *currentMat = pre_step->GetMaterial();
    l.fCsda =
        fEmCalc->GetCSDARange(energy, G4Electron::Definition(), currentMat);
    l.fPreviousMatName = currentMat->GetName();
  }
}

void GateTLEDoseActor::BeginOfEventAction(const G4Event *event) {
  // EM calc does not work at the beginning of the simulation
  {
    G4AutoLock mutex(&SetEkinMaxMutex);
    if (fEmCalc == 0) {
      G4double ekinMax = 0;
      fEmCalc = new G4EmCalculator;
      if ((fTLEThresholdType == 0) || (fTLEThresholdType == 1)) {
        if (fTLEThreshold != std::numeric_limits<double>::infinity()) {
          ekinMax = FindEkinMaxForTLE();
        } else {
          ekinMax = 50 * CLHEP::MeV;
        }
      } else if (fTLEThresholdType == 2) {
        ekinMax = fTLEThreshold;
      }
      if (fTLEThresholdType <= 2)
        fMaterialMuHandler =
            GateMaterialMuHandler::GetInstance(fDatabase, ekinMax);
      else {
        fMaterialMuHandler =
            GateMaterialMuHandler::GetInstance(fDatabase, 5 * CLHEP::MeV);
      }
    }
  }

  auto &l = fThreadLocalData.Get();
  l.fIsTLESecondary = false;
  l.fSecWhichDeposit.clear();
  GateDoseActor::BeginOfEventAction(event);
}
void GateTLEDoseActor::PreUserTrackingAction(const G4Track *track) {
  G4Event *event = G4EventManager::GetEventManager()->GetNonconstCurrentEvent();
  auto &l = fThreadLocalData.Get();
  l.fIsFirstStep = true;
  // If the particle is a gamma, the TLE is initiated as false. The TLE
  // application will be decided in the stepping action depending on the
  // secondary csda range with the gamma energy within the current volume.
  if ((track->GetDefinition()->GetParticleName() == "gamma") ||
      (track->GetParentID() == 0)) {
    l.fIsTLEGamma = false;
    l.fIsTLESecondary = false;
  }
  // if the particle is not a gamma, we want to associate a secondary boolean
  // to allow or not the energy deposition.
  //- If it's a direct secondary, the boolean will be applied according to the
  // tracking information
  // defined in the stepping action according to the csda conditions.
  //- If it's a secondary of a secondary (but not a gamma or not from a gamma
  // secondary), we do nothing,
  // since we already fixed the wyto deposited dose for the mother secondary
  // (electrons or positron).

  else {
    if (track->GetUserInformation() != 0) {
      auto *info = track->GetUserInformation();
      GateUserTrackInformation *trackInfo =
          dynamic_cast<GateUserTrackInformation *>(info);
      l.fIsTLESecondary = trackInfo->GetGateTrackInformation(this);
    }
  }
}

void GateTLEDoseActor::SteppingAction(G4Step *step) {
  auto &l = fThreadLocalData.Get();
  const auto pre_step = step->GetPreStepPoint();

  double energy = 0;
  energy = pre_step->GetKineticEnergy();
  const G4Material *currentMat = pre_step->GetMaterial();
  auto nbSec = step->GetSecondaryInCurrentStep()->size();

  if (fTLEThresholdType <= 1)
    InitializeCSDAForNewGamma(l.fIsFirstStep, step);

  G4double mu_en_over_rho;
  G4double mu_over_rho;

  // At the secondary creation, the TLE status is by default defined as the TLE
  // status of the mother particle Then, if the TLE status has to be changed, it
  // will be modified afterward according to the CSDA range condition.

  SetTLETrackInformationOnSecondaries(step, l.fIsTLESecondary, nbSec);

  if (step->GetTrack()->GetDefinition()->GetParticleName() == "gamma") {
    G4bool tleCondition = false;
    if ((fTLEThresholdType <= 2)) {
      if ((fTLEThresholdType == 0) || (fTLEThresholdType == 1)) {
        auto sec_ekin = energy;
        if (fTLEThresholdType == 1) {
          mu_en_over_rho = fMaterialMuHandler->GetMuEnOverRho(
              pre_step->GetMaterialCutsCouple(), energy);
        }

        if ((energy != l.fPreviousEnergy) ||
            ((pre_step->GetStepStatus() == 1) &&
             (currentMat->GetName() != l.fPreviousMatName))) {
          if (fTLEThresholdType == 1) {
            mu_over_rho = fMaterialMuHandler->GetMuOverRho(
                pre_step->GetMaterialCutsCouple(), energy);
            sec_ekin = energy * mu_en_over_rho / mu_over_rho;
          }
          l.fCsda = fEmCalc->GetCSDARange(sec_ekin, G4Electron::Definition(),
                                          currentMat);
          l.fPreviousMatName = currentMat->GetName();
          l.fPreviousEnergy = energy;
        }
        tleCondition = l.fCsda / CLHEP::mm <= fTLEThreshold;
      }

      else if (fTLEThresholdType == 2) {
        tleCondition = energy / CLHEP::MeV <= fTLEThreshold / CLHEP::MeV;
      }
      // std::cout<<energy<<"   "<<fEnergyMax<<"   "<<tleCondition<<std::endl;
      // std::cout <<tleCondition<<"    "<<energy/ CLHEP::MeV<<"
      // "<<fTLEThreshold/ CLHEP::MeV<<std::endl;
      if (tleCondition) {
        l.fIsTLEGamma = true;
        SetTLETrackInformationOnSecondaries(step, true, nbSec);
      } else {
        l.fIsTLEGamma = false;
        SetTLETrackInformationOnSecondaries(step, false, nbSec);
        return GateDoseActor::SteppingAction(step);
      }
    } else {
      l.fIsTLEGamma = true;
      l.fIsTLESecondary = true;
    }
  }

  // For non-gamma particle, no TLE
  if (step->GetTrack()->GetDefinition()->GetParticleName() != "gamma") {
    if (l.fIsTLESecondary == true) {
      return;
    }
    return GateDoseActor::SteppingAction(step);
  }
  // std::cout<<"TLE"<<std::endl;
  auto weight = step->GetTrack()->GetWeight();
  auto step_length = step->GetStepLength();
  auto density = pre_step->GetMaterial()->GetDensity();
  if (fTLEThresholdType != 1) {
    mu_en_over_rho = fMaterialMuHandler->GetMuEnOverRho(
        pre_step->GetMaterialCutsCouple(), energy);
  }
  // (0.1 because length is in mm -> cm)

  auto edep = weight * 0.1 * energy * mu_en_over_rho * step_length * density /
              (CLHEP::g / CLHEP::cm3);

  // Kill photon below a given energy
  if (energy <= fEnergyMin) {
    edep = weight * energy;
    step->GetTrack()->SetTrackStatus(fStopAndKill);
  }
  const double dose = edep / density;

  // Get the voxel index and check if the step was within the 3D image
  G4ThreeVector position;
  bool isInside;
  Image3DType::IndexType index;
  GetVoxelPosition(step, position, isInside, index);
  const auto event_id =
      G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
  if (isInside) {
    G4AutoLock mutex(&SetPixelTLEMutex); // mutex is bound to the if-scope
    if (fDoseFlag) {
      ImageAddValue<Image3DType>(cpp_dose_image, index, dose);
    }
    ImageAddValue<Image3DType>(cpp_edep_image, index, edep);

    if (fEdepSquaredFlag || fDoseSquaredFlag) {
      if (fEdepSquaredFlag) {
        ScoreSquaredValue(fThreadLocalDataEdep.Get(), cpp_edep_squared_image,
                          edep, event_id, index);
      }
      if (fDoseSquaredFlag) {
        ScoreSquaredValue(fThreadLocalDataDose.Get(), cpp_dose_squared_image,
                          dose, event_id, index);
      }
    }
  }
}
