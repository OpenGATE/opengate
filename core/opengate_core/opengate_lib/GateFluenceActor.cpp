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
}

void GateFluenceActor::InitializeCpp() {
  GateVActor::InitializeCpp();

  // Create the image pointer
  // (the size and allocation will be performed on the py side)
  cpp_fluence_image = Image3DType::New();
}

void GateFluenceActor::BeginOfEventAction(const G4Event *event) {
  G4AutoLock mutex(&SetNbEventMutexFluence);
  NbOfEvent++;
}

void GateFluenceActor::BeginOfRunActionMasterThread(int run_id) {
  // Important ! The volume may have moved, so we (re-)attach each run
  AttachImageToVolume<Image3DType>(cpp_fluence_image, fPhysicalVolumeName,
                                   fTranslation);
  NbOfEvent = 0;
}

void GateFluenceActor::SteppingAction(G4Step *step) {
  // same method to consider only entering tracks
  if (step->GetPreStepPoint()->GetStepStatus() == fGeomBoundary) {
    // the pre-position is at the edge
    auto preGlobal = step->GetPreStepPoint()->GetPosition();
    auto dir = step->GetPreStepPoint()->GetMomentumDirection();
    auto touchable = step->GetPreStepPoint()->GetTouchable();

    // consider position in the local volume, slightly shifted by 0.1 nm because
    // otherwise, it can be considered as outside the volume by isInside.
    auto position = preGlobal + 0.1 * CLHEP::nm * dir;
    auto localPosition =
        touchable->GetHistory()->GetTransform(0).TransformPoint(position);

    // convert G4ThreeVector to itk PointType
    Image3DType::PointType point;
    point[0] = localPosition[0];
    point[1] = localPosition[1];
    point[2] = localPosition[2];

    // get weight
    auto w = step->GetTrack()->GetWeight();

    // get pixel index
    Image3DType::IndexType index;
    bool isInside =
        cpp_fluence_image->TransformPhysicalPointToIndex(point, index);

    // set value
    if (isInside) {
      G4AutoLock FluenceMutex(&SetPixelFluenceMutex);
      ImageAddValue<Image3DType>(cpp_fluence_image, index, w);
    } // else : outside the image
  }
}
