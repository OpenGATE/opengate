/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerProjectionActor.h"
#include "../GateHelpersDict.h"
#include "../GateHelpersImage.h"
#include "GateDigiCollectionManager.h"
#include "GateHelpersDigitizer.h"
#include <G4RunManager.hh>
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
  if (!l.fLocalImage) {
    // The first time a thread reaches here, initialise the input position and
    // local images
    l.fInputPos.resize(fInputDigiCollectionNames.size());
    l.fInputWeights.resize(fInputDigiCollectionNames.size());
    for (size_t slice = 0; slice < fInputDigiCollections.size(); slice++) {
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
    l.fLocalImage = ImageType::New();
    l.fLocalImage->SetRegions(fImage->GetLargestPossibleRegion());
    l.fLocalImage->SetSpacing(fImage->GetSpacing());
    l.fLocalImage->Allocate();
    l.fLocalImage->FillBuffer(0.0);

    // Set size and allocate temporary images
    if (fSquaredImageIsEnabled) {
      l.fLocalSquaredImage = ImageType::New();
      l.fSquaredTempImage = ImageType::New();
      l.fLastEventIdImage = ImageIDType::New();
      l.fLocalSquaredImage->SetRegions(fImage->GetLargestPossibleRegion());
      l.fSquaredTempImage->SetRegions(fImage->GetLargestPossibleRegion());
      l.fLastEventIdImage->SetRegions(fImage->GetLargestPossibleRegion());
      l.fLocalSquaredImage->SetSpacing(fImage->GetSpacing());
      l.fSquaredTempImage->SetSpacing(fImage->GetSpacing());
      l.fLastEventIdImage->SetSpacing(fImage->GetSpacing());
      l.fLocalSquaredImage->Allocate();
      l.fSquaredTempImage->Allocate();
      l.fLastEventIdImage->Allocate();
      l.fLocalSquaredImage->FillBuffer(0.0);
      l.fSquaredTempImage->FillBuffer(0.0);
      l.fLastEventIdImage->FillBuffer(0);
    }
  }

  const auto run_region = GetRunRegion(run->GetRunID());
  itk::ImageRegionIterator<ImageType> iter_local(l.fLocalImage, run_region);
  for (iter_local.GoToBegin(); !iter_local.IsAtEnd(); ++iter_local) {
    iter_local.Set(0.0);
  }
  AttachImageToVolume<ImageType>(l.fLocalImage, fPhysicalVolumeName,
                                 G4ThreeVector(), fDetectorOrientationMatrix);
  if (fSquaredImageIsEnabled) {
    // Each Run we need to set the new orientation to all temp images
    AttachImageToVolume<ImageType>(l.fLocalSquaredImage, fPhysicalVolumeName,
                                   G4ThreeVector(), fDetectorOrientationMatrix);
    AttachImageToVolume<ImageType>(l.fSquaredTempImage, fPhysicalVolumeName,
                                   G4ThreeVector(), fDetectorOrientationMatrix);
    AttachImageToVolume<ImageIDType>(l.fLastEventIdImage, fPhysicalVolumeName,
                                     G4ThreeVector(),
                                     fDetectorOrientationMatrix);
    // end reset to 0 for this run's slices
    itk::ImageRegionIterator<ImageType> iter_sq(l.fLocalSquaredImage,
                                                run_region);
    itk::ImageRegionIterator<ImageType> iter_temp(l.fSquaredTempImage,
                                                  run_region);
    itk::ImageRegionIterator<ImageIDType> iter_id(l.fLastEventIdImage,
                                                  run_region);
    for (iter_sq.GoToBegin(), iter_temp.GoToBegin(), iter_id.GoToBegin();
         !iter_sq.IsAtEnd(); ++iter_sq, ++iter_temp, ++iter_id) {
      iter_sq.Set(0.0);
      iter_temp.Set(0.0);
      iter_id.Set(0);
    }
  }
}

void GateDigitizerProjectionActor::EndOfEventAction(const G4Event * /*event*/) {
  const auto run = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
  for (size_t channel = 0; channel < fInputDigiCollections.size(); channel++) {
    const auto slice = channel + run * fInputDigiCollections.size();
    ProcessSlice(slice, channel);
  }
}

void GateDigitizerProjectionActor::ProcessSlice(const size_t slice,
                                                const size_t channel) const {
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
        ImageAddValue<ImageType>(l.fLocalImage, pindex, weights[i]);
        if (fSquaredImageIsEnabled) {
          // like dose: square must be taken after each event, not each "hit"
          ScoreSquaredValue(pindex, current_event_id, weights[i]);
        }
      } else {
        ImageAddValue<ImageType>(l.fLocalImage, pindex, 1.0);
      }
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
    ImageAddValue<ImageType>(l.fLocalSquaredImage, index, v * v);
    l.fSquaredTempImage->SetPixel(index, value);
    l.fLastEventIdImage->SetPixel(index, current_event_id);
  }
}

GateDigitizerProjectionActor::ImageType::RegionType
GateDigitizerProjectionActor::GetRunRegion(const int run_id) const {
  auto region = fImage->GetLargestPossibleRegion();
  auto index = region.GetIndex();
  auto size = region.GetSize();
  index[2] += run_id * fInputDigiCollections.size();
  size[2] = fInputDigiCollections.size();
  region.SetIndex(index);
  region.SetSize(size);
  return region;
}

void GateDigitizerProjectionActor::EndOfRunAction(const G4Run *run) {
  auto &l = fThreadLocalData.Get();
  const auto run_region = GetRunRegion(run->GetRunID());
  MergeLocalImageToGlobal(l.fLocalImage, fImage, run_region);
  if (fSquaredImageIsEnabled) {
    FlushSquaredValues(run_region);
    MergeLocalImageToGlobal(l.fLocalSquaredImage, fSquaredImage, run_region);
  }
}

void GateDigitizerProjectionActor::FlushSquaredValues(
    const ImageType::RegionType &region) const {
  // When multithreading, the order is unclear, so we do it for all the threads,
  // setting to zero once one is done.
  auto &l = fThreadLocalData.Get();
  itk::ImageRegionIterator<ImageType> iter1(l.fSquaredTempImage, region);
  itk::ImageRegionIterator<ImageType> iter2(l.fLocalSquaredImage, region);
  for (iter1.GoToBegin(), iter2.GoToBegin();
       !iter1.IsAtEnd() && !iter2.IsAtEnd(); ++iter1, ++iter2) {
    if (iter1.Get() != 0.0) {
      // Add the (temp) squared to the current accumulated value
      iter2.Set(iter2.Get() + iter1.Get() * iter1.Get());
      iter1.Set(0.0);
    }
  }
}

void GateDigitizerProjectionActor::MergeLocalImageToGlobal(
    const ImageType::Pointer &local_image,
    const ImageType::Pointer &global_image,
    const ImageType::RegionType &region) const {
  itk::ImageRegionIterator<ImageType> iter1(local_image, region);
  itk::ImageRegionIterator<ImageType> iter2(global_image, region);
  G4AutoLock mutex(&DigitizerProjectionActorMutex);
  for (iter1.GoToBegin(), iter2.GoToBegin();
       !iter1.IsAtEnd() && !iter2.IsAtEnd(); ++iter1, ++iter2) {
    if (iter1.Get() != 0.0) {
      iter2.Set(iter2.Get() + iter1.Get());
      iter1.Set(0.0);
    }
  }
}
