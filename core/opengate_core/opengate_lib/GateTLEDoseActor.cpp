/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateTLEDoseActor.h"
#include "GateHelpersImage.h"
#include "GateMaterialMuHandler.h"
#include "GateTrackDataSlotRegistry.h"
#include "GateUserTrackInformation.h"
#include <G4Electron.hh>
#include <G4EmCalculator.hh>
#include <G4Exception.hh>
#include <G4ParticleDefinition.hh>
#include <G4RunManager.hh>
#include <G4Threading.hh>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <itkAddImageFilter.h>
#include <limits>
#include <vector>

// The edep/dose images are also written by GateDoseActor::SteppingAction
// (non-TLE steps), so the same mutex must protect both paths.
extern G4Mutex SetPixelMutex;
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
  fSplitStepInVoxels = py::cast<bool>(user_info["split_step_in_voxels"]);
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

void GateTLEDoseActor::InitializeCpp() {
  GateDoseActor::InitializeCpp();
  fLegacyTLETrackDataSlotID = GateTrackDataSlotRegistry::RegisterSlot(
      "actor_" + GetName() + "_tle_secondary_suppressed", "actor", GetName(),
      "int");
}

void GateTLEDoseActor::SetTLETrackInformationOnSecondaries(G4Step *step,
                                                           G4bool info,
                                                           G4int nbSec) {
  if (nbSec > 0) {
    for (auto i = 0; i < nbSec; i++) {
      auto *secs = step->GetfSecondary();
      auto *sec = (*secs)[secs->size() - i - 1];
      auto *track_info = GetOrCreateGateUserTrackInformation(sec);
      auto *track_data = track_info->GetOrCreateTrackData<GateIntTrackData>(
          fLegacyTLETrackDataSlotID);
      track_data->SetValue(static_cast<int>(info));
    }
  }
}

G4EmCalculator &GateTLEDoseActor::GetEmCalc() {
  auto &l = fThreadLocalData.Get();
  if (!l.fEmCalc) {
    l.fEmCalc = std::make_unique<G4EmCalculator>();
  }
  return *l.fEmCalc;
}

G4double GateTLEDoseActor::FindEkinMaxForTLE() {
  G4MaterialTable *matTable = G4Material::GetMaterialTable();
  G4int nbOfMaterials = G4Material::GetNumberOfMaterials();
  G4double ekinMax = 0;
  auto &emCalc = GetEmCalc();
  for (G4int i = 0; i < nbOfMaterials; i++) {
    G4Material *currentMat = (*matTable)[i];
    G4double ekin = emCalc.GetKinEnergy(fTLEThreshold, G4Electron::Definition(),
                                        currentMat);
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
        GetEmCalc().GetCSDARange(energy, G4Electron::Definition(), currentMat);
    l.fPreviousMatName = currentMat->GetName();
  }
}

void GateTLEDoseActor::BeginOfEventAction(const G4Event *event) {
  // EM calc does not work at the beginning of the simulation
  {
    G4AutoLock mutex(&SetEkinMaxMutex);
    if (!fMaterialMuHandler) {
      G4double ekinMax = 0;
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
      fMaterialMuHandler->Initialize();
    }
  }

  auto &l = fThreadLocalData.Get();
  l.fIsTLESecondary = false;
  l.fSecWhichDeposit.clear();
  GateDoseActor::BeginOfEventAction(event);
}
void GateTLEDoseActor::PreUserTrackingAction(const G4Track *track) {
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
      auto *track_info = GetGateUserTrackInformation(track);
      if (track_info != nullptr) {
        auto *track_data = track_info->GetTrackData<GateIntTrackData>(
            fLegacyTLETrackDataSlotID);
        if (track_data != nullptr) {
          l.fIsTLESecondary = static_cast<bool>(track_data->GetValue());
        }
      }
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
          l.fCsda = GetEmCalc().GetCSDARange(sec_ekin, G4Electron::Definition(),
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
  ScoreTLEDepositStep(step);
}

void GateTLEDoseActor::ScoreTLEDepositStep(G4Step *step) {
  const auto pre_step = step->GetPreStepPoint();
  auto energy = pre_step->GetKineticEnergy();
  auto weight = step->GetTrack()->GetWeight();
  auto step_length = step->GetStepLength();
  auto density = pre_step->GetMaterial()->GetDensity();
  G4double mu_en_over_rho;
  if (fTLEThresholdType != 1) {
    mu_en_over_rho = fMaterialMuHandler->GetMuEnOverRho(
        pre_step->GetMaterialCutsCouple(), energy);
  } else {
    mu_en_over_rho = fMaterialMuHandler->GetMuEnOverRho(
        pre_step->GetMaterialCutsCouple(), energy);
  }
  auto edep = weight * 0.1 * energy * mu_en_over_rho * step_length * density /
              (CLHEP::g / CLHEP::cm3);

  if (energy <= fEnergyMin) {
    edep = weight * energy;
    step->GetTrack()->SetTrackStatus(fStopAndKill);
  }
  const auto event_id =
      G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
  if (fSplitStepInVoxels && energy > fEnergyMin) {
    ScoreTLEDepositSplit(step, edep, density, event_id);
    return;
  }

  const double dose = edep / density;

  G4ThreeVector position;
  bool isInside;
  Image3DType::IndexType index;
  GetVoxelPosition(step, position, isInside, index);
  if (isInside) {
    // all ImageAddValue calls in a mutex-scope
    {
      G4AutoLock mutex(&SetPixelMutex);
      if (fDoseFlag) {
        ImageAddValue<Image3DType>(cpp_dose_image, index, dose);
      }
      ImageAddValue<Image3DType>(cpp_edep_image, index, edep);
    } // mutex scope

    // ScoreSquaredValue() is thread-safe because it contains a mutex
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

void GateTLEDoseActor::ScoreTLEDepositSplit(G4Step *step, const double edep,
                                            const double density,
                                            const int event_id) {
  // the pre and post points in the frame of the dose image (as in
  // GateDoseActor::GetVoxelPosition)
  const auto *touchable = step->GetPreStepPoint()->GetTouchable();
  const auto &transform = touchable->GetHistory()->GetTransform(0);
  const auto pre =
      transform.TransformPoint(step->GetPreStepPoint()->GetPosition());
  const auto post =
      transform.TransformPoint(step->GetPostStepPoint()->GetPosition());

  // continuous index, shifted so that voxel i spans [i, i+1) on each axis
  Image3DType::PointType p0, p1;
  for (int k = 0; k < 3; k++) {
    p0[k] = pre[k];
    p1[k] = post[k];
  }
  const auto c0 =
      cpp_edep_image->TransformPhysicalPointToContinuousIndex<double, double>(
          p0);
  const auto c1 =
      cpp_edep_image->TransformPhysicalPointToContinuousIndex<double, double>(
          p1);
  const auto size = cpp_edep_image->GetLargestPossibleRegion().GetSize();
  double a[3], d[3];
  for (int k = 0; k < 3; k++) {
    a[k] = c0[k] + 0.5;
    d[k] = c1[k] + 0.5 - a[k];
  }

  // clip the segment a + t d, t in [0, 1], to the image box [0, size]
  double t0 = 0, t1 = 1;
  for (int k = 0; k < 3; k++) {
    const double n = static_cast<double>(size[k]);
    if (d[k] == 0) {
      if (a[k] < 0 || a[k] >= n)
        return;
      continue;
    }
    double ta = (0 - a[k]) / d[k];
    double tb = (n - a[k]) / d[k];
    if (ta > tb)
      std::swap(ta, tb);
    t0 = std::max(t0, ta);
    t1 = std::min(t1, tb);
  }
  if (t0 >= t1)
    return;

  // voxel walk (Amanatides and Woo 1987); the weight of a voxel is the
  // fraction of the step length (in t) inside it
  Image3DType::IndexType index;
  int step_dir[3];
  double t_max[3], t_delta[3];
  // the entry voxel: the one of a point just after the entry, so that a
  // step starting exactly on a face gets the voxel it goes into
  const double t_in = t0 + std::min(1e-9, 0.5 * (t1 - t0));
  for (int k = 0; k < 3; k++) {
    long i = static_cast<long>(std::floor(a[k] + t_in * d[k]));
    i = std::min(std::max(i, 0L), static_cast<long>(size[k]) - 1);
    index[k] = i;
    if (d[k] > 0) {
      step_dir[k] = 1;
      t_max[k] = (static_cast<double>(i + 1) - a[k]) / d[k];
      t_delta[k] = 1.0 / d[k];
    } else if (d[k] < 0) {
      step_dir[k] = -1;
      t_max[k] = (static_cast<double>(i) - a[k]) / d[k];
      t_delta[k] = -1.0 / d[k];
    } else {
      step_dir[k] = 0;
      t_max[k] = std::numeric_limits<double>::infinity();
      t_delta[k] = std::numeric_limits<double>::infinity();
    }
  }

  // collect the (voxel, weight) pairs, then add them under one lock
  thread_local std::vector<std::pair<Image3DType::IndexType, double>> hits;
  hits.clear();
  double t = t0;
  const std::size_t max_iter = size[0] + size[1] + size[2] + 3;
  for (std::size_t it = 0; it < max_iter && t < t1; it++) {
    int k = 0;
    if (t_max[1] < t_max[k])
      k = 1;
    if (t_max[2] < t_max[k])
      k = 2;
    const double t_next = std::min(t_max[k], t1);
    if (t_next > t)
      hits.emplace_back(index, t_next - t);
    t = t_next;
    if (t >= t1)
      break;
    index[k] += step_dir[k];
    if (index[k] < 0 || index[k] >= static_cast<long>(size[k]))
      break;
    t_max[k] += t_delta[k];
  }
  if (hits.empty())
    return;

  {
    G4AutoLock mutex(&SetPixelMutex);
    for (const auto &[idx, w] : hits) {
      if (fDoseFlag) {
        ImageAddValue<Image3DType>(cpp_dose_image, idx, w * edep / density);
      }
      ImageAddValue<Image3DType>(cpp_edep_image, idx, w * edep);
    }
  }
  if (fEdepSquaredFlag || fDoseSquaredFlag) {
    for (const auto &[idx, w] : hits) {
      if (fEdepSquaredFlag) {
        ScoreSquaredValue(fThreadLocalDataEdep.Get(), cpp_edep_squared_image,
                          w * edep, event_id, idx);
      }
      if (fDoseSquaredFlag) {
        ScoreSquaredValue(fThreadLocalDataDose.Get(), cpp_dose_squared_image,
                          w * edep / density, event_id, idx);
      }
    }
  }
}
