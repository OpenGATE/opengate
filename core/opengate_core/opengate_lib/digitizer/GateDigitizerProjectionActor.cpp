/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerProjectionActor.h"
#include "../GateHelpersDict.h"
#include "../GateHelpersImage.h"
#include "G4RunManager.hh"
#include "GateDigiCollectionManager.h"
#include <iostream>

G4Mutex DigitizerProjectionActorMutex = G4MUTEX_INITIALIZER;

GateDigitizerProjectionActor::GateDigitizerProjectionActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  fActions.insert("StartSimulationAction");
  fActions.insert("EndOfEventAction");
  fActions.insert("BeginOfRunAction");
  fPhysicalVolumeName = "None";
  fEnableSquaredImage = false;
  fImage = nullptr;
}

GateDigitizerProjectionActor::~GateDigitizerProjectionActor() = default;

void GateDigitizerProjectionActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  auto r = DictGetMatrix(user_info, "detector_orientation_matrix");
  fDetectorOrientationMatrix = ConvertToG4RotationMatrix(r);
  fInputDigiCollectionNames =
      DictGetVecStr(user_info, "input_digi_collections");
}

void GateDigitizerProjectionActor::InitializeCpp() {
  fImage = ImageType::New();
  fSquaredImage = ImageType::New();
}

void GateDigitizerProjectionActor::SetPhysicalVolumeName(
    const std::string &name) {
  fPhysicalVolumeName = name;
}

void GateDigitizerProjectionActor::EnableSquaredImage(const bool b) {
  fEnableSquaredImage = b;
  // FIXME check if weight exists ?
}

// Called when the simulation starts
void GateDigitizerProjectionActor::StartSimulationAction() {
  // Get the input hits collection
  auto *hcm = GateDigiCollectionManager::GetInstance();
  for (const auto &name : fInputDigiCollectionNames) {
    auto *hc = hcm->GetDigiCollection(name);
    fInputDigiCollections.push_back(hc);
    CheckRequiredAttribute(hc, "PostPosition");
  }
}

void GateDigitizerProjectionActor::BeginOfRunActionMasterThread(int run_id) {
  // Set the image to the correct position/orientation
  AttachImageToVolume<ImageType>(fImage, fPhysicalVolumeName, G4ThreeVector(),
                                 fDetectorOrientationMatrix);
  AttachImageToVolume<ImageType>(fSquaredImage, fPhysicalVolumeName,
                                 G4ThreeVector(), fDetectorOrientationMatrix);
}

void GateDigitizerProjectionActor::BeginOfRunAction(const G4Run *run) {
  auto &l = fThreadLocalData.Get();
  if (run->GetRunID() == 0) {
    // The first time here we need to initialize the input position
    l.fInputPos.resize(fInputDigiCollectionNames.size());
    l.fInputWeights.resize(fInputDigiCollectionNames.size());
    for (int slice = 0; slice < fInputDigiCollections.size(); slice++) {
      auto *att_pos =
          fInputDigiCollections[slice]->GetDigiAttribute("PostPosition");
      l.fInputPos[slice] = &att_pos->Get3Values();

      // weight ?
      try {
        auto *att_w = fInputDigiCollections[slice]->GetDigiAttribute("Weight");
        l.fInputWeights[slice] = &att_w->GetDValues();
      } catch (std::runtime_error &) {
        // No weights attribute
        l.fInputWeights[slice] = new std::vector<double>;
        l.fInputWeights[slice]->clear();
      }
    }
  }
}

void GateDigitizerProjectionActor::EndOfEventAction(const G4Event * /*event*/) {
  G4AutoLock mutex(&DigitizerProjectionActorMutex);
  const auto run = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
  for (size_t channel = 0; channel < fInputDigiCollections.size(); channel++) {
    auto slice = channel + run * fInputDigiCollections.size();
    ProcessSlice(slice, channel);
  }
}

void GateDigitizerProjectionActor::ProcessSlice(const long slice,
                                                const size_t channel) const {
  auto &l = fThreadLocalData.Get();
  const auto *hc = fInputDigiCollections[channel];
  const auto index = hc->GetBeginOfEventIndex();
  auto n = hc->GetSize() - index;
  // If no new hits, do nothing
  if (n <= 0)
    return;

  // FIXME store other attributes somewhere ?
  const auto &pos = *l.fInputPos[channel];
  const auto &weights = *l.fInputWeights[channel];
  ImageType::PointType point;
  ImageType::IndexType pindex;

  // loop on channels
  for (size_t i = index; i < hc->GetSize(); i++) {
    // get position from the input collection
    for (auto j = 0; j < 3; j++)
      point[j] = pos[i][j];

    bool isInside = fImage->TransformPhysicalPointToIndex(point, pindex);
    if (isInside) {
      // force the slice according to the channel
      pindex[2] = slice;

      // Take particle weight into account (if in the attribute list)
      if (!weights.empty()) {
        ImageAddValue<ImageType>(fImage, pindex,
                                 static_cast<float>(weights[i]));
        if (fEnableSquaredImage)
          ImageAddValue<ImageType>(fSquaredImage, pindex,
                                   static_cast<float>(weights[i] * weights[i]));
      } else
        ImageAddValue<ImageType>(fImage, pindex, 1.0);
    } else {
      // Should never be here (?)
      /*DDDV(pos);
      DDE(point);
      DDE(isInside);
      DDE(pindex);
      DDE(slice);
      DDE(fImage->GetLargestPossibleRegion().GetSize());
      nout++;
      DDE(nout);*/
    }
  }
}
