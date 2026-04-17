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
  fsize = DictGetG4ThreeVector(user_info, "size");
  fspacing = DictGetG4ThreeVector(user_info, "spacing");
}

void GateClusterDoseActor::InitializeCpp() {
  GateVActor::InitializeCpp();
  cpp_cluster_dose_image = Image4DType::New();
  cpp_cluster_volume_image = Image3DType::New();

  Image3DType::RegionType region;
  Image3DType::SizeType size;
  Image3DType::SpacingType spacing;

  size[0] = fsize[0];
  size[1] = fsize[1];
  size[2] = fsize[2];
  region.SetSize(size);

  spacing[0] = fspacing[0];
  spacing[1] = fspacing[1];
  spacing[2] = fspacing[2];

  cpp_cluster_volume_image->SetRegions(region);
  cpp_cluster_volume_image->SetSpacing(spacing);
  cpp_cluster_volume_image->Allocate();
  cpp_cluster_volume_image->FillBuffer(0);
}

void GateClusterDoseActor::BeginOfEventAction(const G4Event * /*event*/) {
  G4AutoLock mutex(&SetNbEventMutexClusterDose);
  NbOfEvent++;
}

void GateClusterDoseActor::BeginOfRunActionMasterThread(int run_id) {
  cpp_cluster_dose_image->FillBuffer(0);
  AttachImageToVolume<Image3DType>(cpp_cluster_volume_image, fPhysicalVolumeName,
                                   fTranslation);
  NbOfEvent = 0;
}

double GateClusterDoseActor::InterpolateCumulativeValue(const size_t channelIndex,
                                                        const double energy) const {
  if (channelIndex >= fClusterDatabaseEnergyGrid.size() ||
      channelIndex >= fClusterDatabaseCumulativeValues.size()) {
    return 0.0;
  }

  const auto &energyGrid = fClusterDatabaseEnergyGrid[channelIndex];
  const auto &cumulativeValues = fClusterDatabaseCumulativeValues[channelIndex];
  if (energyGrid.empty() || cumulativeValues.empty() ||
      energyGrid.size() != cumulativeValues.size()) {
    return 0.0;
  }

  if (energy <= energyGrid.front()) {
    return cumulativeValues.front();
  }
  if (energy >= energyGrid.back()) {
    return cumulativeValues.back();
  }

  const auto upper = std::upper_bound(energyGrid.begin(), energyGrid.end(), energy);
  const auto upperIndex =
      static_cast<size_t>(std::distance(energyGrid.begin(), upper));
  const auto lowerIndex = upperIndex - 1;

  const auto e0 = energyGrid[lowerIndex];
  const auto e1 = energyGrid[upperIndex];
  const auto f0 = cumulativeValues[lowerIndex];
  const auto f1 = cumulativeValues[upperIndex];

  if (e1 == e0) {
    return f0;
  }

  const auto weight = (energy - e0) / (e1 - e0);
  return f0 + weight * (f1 - f0);
}

void GateClusterDoseActor::SteppingAction(G4Step *step) {
  G4ThreeVector position;
  bool isInside = false;
  Image3DType::IndexType spatialIndex;
  GetStepVoxelPosition<Image3DType>(step, fHitType, cpp_cluster_volume_image,
                                    position, isInside, spatialIndex);

  if (!isInside) {
    return;
  }

  const auto preEnergy = step->GetPreStepPoint()->GetKineticEnergy() / CLHEP::MeV;
  const auto postEnergy =
      step->GetPostStepPoint()->GetKineticEnergy() / CLHEP::MeV;

  G4AutoLock mutex(&SetPixelClusterDoseMutex);
  for (size_t channelIndex = 0; channelIndex < fClusterDatabaseEnergyGrid.size();
       ++channelIndex) {
    const auto value =
        std::abs(InterpolateCumulativeValue(channelIndex, preEnergy) -
                 InterpolateCumulativeValue(channelIndex, postEnergy));
    if (value <= 0.0) {
      continue;
    }
    Image4DType::IndexType index4D;
    index4D[0] = spatialIndex[0];
    index4D[1] = spatialIndex[1];
    index4D[2] = spatialIndex[2];
    index4D[3] = static_cast<long>(channelIndex);
    ImageAddValue<Image4DType>(cpp_cluster_dose_image, index4D, value);
  }
}
