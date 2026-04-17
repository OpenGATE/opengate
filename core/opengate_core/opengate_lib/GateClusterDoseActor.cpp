/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateClusterDoseActor.h"

#include "G4RandomTools.hh"

#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

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
  fClusterSizeDatabase = DictGetStr(user_info, "cluster_size_database");
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

void GateClusterDoseActor::SteppingAction(G4Step *step) {
  G4ThreeVector position;
  bool isInside = false;
  Image3DType::IndexType index;
  GetStepVoxelPosition<Image3DType>(step, fHitType, cpp_cluster_dose_image,
                                    position, isInside, index);

  if (!isInside) {
    return;
  }

  // Temporary scaffold: score a deterministic non-zero value so the full actor
  // pipeline can be validated before the cluster lookup-table logic lands.
  const auto value = static_cast<double>(fClusterSize);

  G4AutoLock mutex(&SetPixelClusterDoseMutex);
  ImageAddValue<Image3DType>(cpp_cluster_dose_image, index, value);
}
