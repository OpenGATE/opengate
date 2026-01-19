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
#include <itkImageRegionIterator.h>

G4Mutex DigitizerProjectionActorMutex = G4MUTEX_INITIALIZER;

GateDigitizerProjectionActor::GateDigitizerProjectionActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  fActions.insert("StartSimulationAction");
  fActions.insert("EndOfEventAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("EndOfRunAction");
  fPhysicalVolumeName = "None";
  fSquaredImageIsEnabled = false;
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
  fSquaredImageIsEnabled = b;
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
    // The first time here we need to initialise the input position
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
    // Set size and allocate temporary images
    if (fSquaredImageIsEnabled) {
      l.fSquaredTempImage = ImageType::New();
      l.fLastEventIdImage = ImageIDType::New();
      l.fSquaredTempImage->SetRegions(fImage->GetLargestPossibleRegion());
      l.fLastEventIdImage->SetRegions(fImage->GetLargestPossibleRegion());
      l.fSquaredTempImage->Allocate();
      l.fLastEventIdImage->Allocate();
    }
  }

  if (fSquaredImageIsEnabled) {
    // Each Run we need to set the new orientation to all temp images
    AttachImageToVolume<ImageType>(l.fSquaredTempImage, fPhysicalVolumeName,
                                   G4ThreeVector(), fDetectorOrientationMatrix);
    AttachImageToVolume<ImageIDType>(l.fLastEventIdImage, fPhysicalVolumeName,
                                     G4ThreeVector(),
                                     fDetectorOrientationMatrix);
    // end reset to 0
    l.fSquaredTempImage->FillBuffer(0.0);
    l.fLastEventIdImage->FillBuffer(0);
  }
}

void GateDigitizerProjectionActor::EndOfEventAction(const G4Event * /*event*/) {
  G4AutoLock mutex(&DigitizerProjectionActorMutex);
  const auto run = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
  for (size_t channel = 0; channel < fInputDigiCollections.size(); channel++) {
    const auto slice = channel + run * fInputDigiCollections.size();
    ProcessSlice(slice, channel);
  }
}

void GateDigitizerProjectionActor::ProcessSlice(const size_t slice,
                                                const size_t channel) const {
  // (Note: this is called during EndOfEventAction and in a mutex scope)
  const auto &l = fThreadLocalData.Get();
  const auto *hc = fInputDigiCollections[channel];
  const auto index = hc->GetBeginOfEventIndex();
  const auto n = hc->GetSize() - index;
  // If no new hits, do nothing
  if (n <= 0)
    return;

  // FIXME store other attributes somewhere ?
  const auto &pos = *l.fInputPos[channel];
  const auto &weights = *l.fInputWeights[channel];
  ImageType::PointType point;
  ImageType::IndexType pindex;
  const auto current_event_id =
      G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();

  // loop on channels
  for (size_t i = index; i < hc->GetSize(); i++) {
    // get position from the input collection
    for (auto j = 0; j < 3; j++)
      point[j] = pos[i][j];

    const bool isInside = fImage->TransformPhysicalPointToIndex(point, pindex);
    if (isInside) {
      // force the slice according to the channel
      pindex[2] = slice;

      // Take particle weight into account (if in the attribute list)
      if (!weights.empty()) {
        ImageAddValue<ImageType>(fImage, pindex, weights[i]);
        if (fSquaredImageIsEnabled) {
          // like dose: square must be taken after each event, not each "hit"
          ScoreSquaredValue(pindex, current_event_id, weights[i]);
        }
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
      */
    }
  }
}

void GateDigitizerProjectionActor::ScoreSquaredValue(
    const ImageType::IndexType &index, const int current_event_id,
    const double value) const {
  const auto &l = fThreadLocalData.Get();
  auto previous_event_id = l.fLastEventIdImage->GetPixel(index);
  if (previous_event_id == current_event_id) {
    // If the current event id is the same as the one at the pixel, we just sum
    // the values
    // DDD(previous_event_id);
    // DDD(value);
    ImageAddValue<ImageType>(l.fSquaredTempImage, index, value);
  } else {
    // If it is different, we square the deposited value from the last event id
    // and start accumulating for this new event.
    const auto v = l.fSquaredTempImage->GetPixel(index);
    // DDD(v);
    ImageAddValue<ImageType>(fSquaredImage, index, v * v);
    l.fSquaredTempImage->SetPixel(index, value);
    l.fLastEventIdImage->SetPixel(index, current_event_id);
  }
}

void GateDigitizerProjectionActor::EndOfRunAction(const G4Run *run) {
  if (fSquaredImageIsEnabled)
    FlushSquaredValues();
}

void GateDigitizerProjectionActor::FlushSquaredValues() const {
  // When multithreading, the order is unclear, so we do it for all the threads,
  // setting to zero once one is done.
  auto &l = fThreadLocalData.Get();
  itk::ImageRegionIterator<ImageType> iter1(
      l.fSquaredTempImage, l.fSquaredTempImage->GetLargestPossibleRegion());
  itk::ImageRegionIterator<ImageType> iter2(
      fSquaredImage, fSquaredImage->GetLargestPossibleRegion());
  G4AutoLock mutex(&DigitizerProjectionActorMutex);
  for (iter1.GoToBegin(), iter2.GoToBegin();
       !iter1.IsAtEnd() && !iter2.IsAtEnd(); ++iter1, ++iter2) {
    if (iter1.Get() != 0.0) {
      // Add the (temp) squared to the current accumulated value
      iter2.Set(iter2.Get() + iter1.Get() * iter1.Get());
      iter1.Set(0.0);
    }
  }
}
