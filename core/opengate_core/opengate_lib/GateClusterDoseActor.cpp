/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateClusterDoseActor.h"

#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

#include <algorithm>
#include <cmath>

G4Mutex SetPixelClusterDoseMutex = G4MUTEX_INITIALIZER;
G4Mutex SetNbEventMutexClusterDose = G4MUTEX_INITIALIZER;

GateClusterDoseActor::GateClusterDoseActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  fActions.insert("SteppingAction");
}

void GateClusterDoseActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  fTranslation = DictGetG4ThreeVector(user_info, "translation");
  fHitType = DictGetStr(user_info, "hit_type");
  fClusterSize = DictGetInt(user_info, "cluster_size");
}

void GateClusterDoseActor::InitializeCpp() {
  GateVActor::InitializeCpp();
  cpp_cluster_dose_image = Image3DType::New();
}

void GateClusterDoseActor::BeginOfEventAction(const G4Event * /*event*/) {
  G4AutoLock mutex(&SetNbEventMutexClusterDose);
  NbOfEvent++;
}

void GateClusterDoseActor::BeginOfRunActionMasterThread(int run_id) {
  AttachImageToVolume<Image3DType>(cpp_cluster_dose_image, fPhysicalVolumeName,
                                   fTranslation);
  NbOfEvent = 0;
}

double GateClusterDoseActor::InterpolateCumulativeValue(const double energy) const {
  if (fClusterDatabaseEnergyGrid.empty() ||
      fClusterDatabaseCumulativeValues.empty() ||
      fClusterDatabaseEnergyGrid.size() != fClusterDatabaseCumulativeValues.size()) {
    return 0.0;
  }

  if (energy <= fClusterDatabaseEnergyGrid.front()) {
    return fClusterDatabaseCumulativeValues.front();
  }
  if (energy >= fClusterDatabaseEnergyGrid.back()) {
    return fClusterDatabaseCumulativeValues.back();
  }

  const auto upper = std::upper_bound(fClusterDatabaseEnergyGrid.begin(),
                                      fClusterDatabaseEnergyGrid.end(), energy);
  const auto upperIndex =
      static_cast<size_t>(std::distance(fClusterDatabaseEnergyGrid.begin(), upper));
  const auto lowerIndex = upperIndex - 1;

  const auto e0 = fClusterDatabaseEnergyGrid[lowerIndex];
  const auto e1 = fClusterDatabaseEnergyGrid[upperIndex];
  const auto f0 = fClusterDatabaseCumulativeValues[lowerIndex];
  const auto f1 = fClusterDatabaseCumulativeValues[upperIndex];

  if (e1 == e0) {
    return f0;
  }

  const auto weight = (energy - e0) / (e1 - e0);
  return f0 + weight * (f1 - f0);
}

void GateClusterDoseActor::SteppingAction(G4Step *step) {
  G4ThreeVector position;
  bool isInside = false;
  Image3DType::IndexType index;
  GetStepVoxelPosition<Image3DType>(step, fHitType, cpp_cluster_dose_image,
                                    position, isInside, index);

  if (!isInside) {
    return;
  }

  const auto preEnergy =
      step->GetPreStepPoint()->GetKineticEnergy() / CLHEP::MeV;
  const auto postEnergy =
      step->GetPostStepPoint()->GetKineticEnergy() / CLHEP::MeV;
  (void)fClusterSize;

  const auto value =
      std::abs(InterpolateCumulativeValue(preEnergy) -
               InterpolateCumulativeValue(postEnergy));
  if (value <= 0.0) {
    return;
  }

  G4AutoLock mutex(&SetPixelClusterDoseMutex);
  ImageAddValue<Image3DType>(cpp_cluster_dose_image, index, value);
}
