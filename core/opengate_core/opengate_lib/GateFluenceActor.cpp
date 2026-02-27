/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "G4Navigator.hh"
#include "G4RunManager.hh"
#include "G4Threading.hh"

#include "GateFluenceActor.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

#include <iostream>
#include <itkAddImageFilter.h>
#include <itkImageRegionIterator.h>

// Mutex that will be used by thread to write the output image
G4Mutex SetPixelFluenceMutex = G4MUTEX_INITIALIZER;
G4Mutex SetNbEventMutexFluence = G4MUTEX_INITIALIZER;

GateFluenceActor::GateFluenceActor(py::dict &user_info)
    : GateVActor(user_info, true) {

  // Action for this actor: during stepping
  fActions.insert("SteppingAction");
  fActions.insert("BeginOfRunAction");
}

void GateFluenceActor::InitializeUserInfo(py::dict &user_info) {
  // IMPORTANT: call the base class method
  GateVActor::InitializeUserInfo(user_info);
  fTranslation = DictGetG4ThreeVector(user_info, "translation");
  fHitType = DictGetStr(user_info, "hit_type");
}

void GateFluenceActor::InitializeCpp() {
  GateVActor::InitializeCpp();

  // Create the image pointer
  // (the size and allocation will be performed on the py side)
  cpp_fluence_image = Image3DType::New();

  // Create sum_tracks image if needed based on scoring mode
  if (fFluenceScoringMode == "sum_tracks") {
    cpp_fluence_sum_tracks_image = Image3DType::New();
  }
}

void GateFluenceActor::BeginOfEventAction(const G4Event *event) {
  G4AutoLock mutex(&SetNbEventMutexFluence);
  NbOfEvent++;
}

void GateFluenceActor::BeginOfRunActionMasterThread(int run_id) {
  // Important ! The volume may have moved, so we (re-)attach each run

  if (fFluenceScoringMode == "fluence") {
    AttachImageToVolume<Image3DType>(cpp_fluence_image, fPhysicalVolumeName,
                                     fTranslation);
    auto sp = cpp_fluence_image->GetSpacing();
    fVoxelVolume = sp[0] * sp[1] * sp[2];
  } else if (fFluenceScoringMode == "sum_tracks") {
    AttachImageToVolume<Image3DType>(cpp_fluence_sum_tracks_image,
                                     fPhysicalVolumeName, fTranslation);
    auto sp = cpp_fluence_sum_tracks_image->GetSpacing();
    fVoxelVolume = sp[0] * sp[1] * sp[2];
  }

  NbOfEvent = 0;
}

void GateFluenceActor::GetVoxelPosition(G4Step *step, G4ThreeVector &position,
                                        bool &isInside,
                                        Image3DType::IndexType &index,
                                        Image3DType::Pointer &image) const {
  auto preGlobal = step->GetPreStepPoint()->GetPosition();
  auto postGlobal = step->GetPostStepPoint()->GetPosition();
  auto touchable = step->GetPreStepPoint()->GetTouchable();

  // consider random position between pre and post
  if (fHitType == "pre") {
    position = preGlobal;
  }
  if (fHitType == "post") {
    position = postGlobal;
  }
  if (fHitType == "random") {
    auto x = G4UniformRand();
    auto direction = postGlobal - preGlobal;
    position = preGlobal + x * direction;
  }
  if (fHitType == "middle") {
    auto direction = postGlobal - preGlobal;
    position = preGlobal + 0.5 * direction;
  }

  auto localPosition =
      touchable->GetHistory()->GetTransform(0).TransformPoint(position);

  // convert G4ThreeVector to itk PointType
  Image3DType::PointType point;
  point[0] = localPosition[0];
  point[1] = localPosition[1];
  point[2] = localPosition[2];

  isInside = image->TransformPhysicalPointToIndex(point, index);
}

void GateFluenceActor::SteppingAction(G4Step *step) {

  const auto event_id =
      G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
  auto preGlobal = step->GetPreStepPoint()->GetPosition();
  auto postGlobal = step->GetPostStepPoint()->GetPosition();

  // FIXME If the volume has multiple copy, touchable->GetCopyNumber(0) ?

  // Get the voxel index
  G4ThreeVector position;
  bool isInside;
  Image3DType::IndexType index;
  if (fFluenceScoringMode == "fluence") {
    GetVoxelPosition(step, position, isInside, index, cpp_fluence_image);
  } else if (fFluenceScoringMode == "sum_tracks") {
    GetVoxelPosition(step, position, isInside, index,
                     cpp_fluence_sum_tracks_image);
  }

  if (isInside) {

    auto w = step->GetPreStepPoint()->GetWeight();
    double step_length = step->GetStepLength() / CLHEP::mm * w;

    {
      G4AutoLock FluenceMutex(&SetPixelFluenceMutex);
      // Score based on selected mode
      if (fFluenceScoringMode == "fluence") {
        // Score fluence only at geometric boundaries
        if (step->GetPreStepPoint()->GetStepStatus() == fGeomBoundary) {
          ImageAddValue<Image3DType>(cpp_fluence_image, index, w);
        }
      } else if (fFluenceScoringMode == "sum_tracks") {
        // Score track length density for all steps
        ImageAddValue<Image3DType>(cpp_fluence_sum_tracks_image, index,
                                   step_length / fVoxelVolume);
      }
    }
  }
}
