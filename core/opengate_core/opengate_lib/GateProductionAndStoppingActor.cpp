/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateProductionAndStoppingActor.h"
#include "G4Navigator.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

#include "G4Deuteron.hh"
#include "G4Electron.hh"
#include "G4EmCalculator.hh"
#include "G4Gamma.hh"
#include "G4MaterialTable.hh"
#include "G4NistManager.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleTable.hh"
#include "G4Positron.hh"
#include "G4Proton.hh"

// Mutex that will be used by thread to write in the values to the image
G4Mutex SetProdStopPixelMutex = G4MUTEX_INITIALIZER;

GateProductionAndStoppingActor::GateProductionAndStoppingActor(
    py::dict &user_info)
    : GateVActor(user_info, true) {
  // Action for this actor: during stepping
  fActions.insert("SteppingAction");
  fActions.insert("PostUserTrackingAction");
}

void GateProductionAndStoppingActor::InitializeUserInfo(py::dict &user_info) {
  // IMPORTANT: call the base class method
  GateVActor::InitializeUserInfo(user_info);

  fMethod = DictGetStr(user_info, "method");
  if (fMethod == "production") {
    fProductionImageEnabled = true;
    fStopImageEnabled = !fProductionImageEnabled;

  } else if (fMethod == "stopping") {
    fProductionImageEnabled = false;
    fStopImageEnabled = !fProductionImageEnabled;
  }

  fInitialTranslation = DictGetG4ThreeVector(user_info, "translation");
  // Hit type (random, pre, post etc)
  fHitType = DictGetStr(user_info, "hit_type");
}

void GateProductionAndStoppingActor::InitializeCpp() {
  // Create the image pointer
  // (the size and allocation will be performed on the py side)
  cpp_value_image = ImageType::New();
}

void GateProductionAndStoppingActor::BeginOfRunActionMasterThread(int run_id) {
  // Important ! The volume may have moved, so we re-attach each run
  AttachImageToVolume<ImageType>(cpp_value_image, fPhysicalVolumeName,
                                 fInitialTranslation);
  // compute volume of a dose voxel
  auto sp = cpp_value_image->GetSpacing();
  fVoxelVolume = sp[0] * sp[1] * sp[2];
}

void GateProductionAndStoppingActor::SteppingAction(G4Step *step) {
  //
  if (fProductionImageEnabled) {
    if (step->GetTrack()->GetCurrentStepNumber() == 1) {
      AddValueToImage(step);
    }
  }
}
void GateProductionAndStoppingActor::PostUserTrackingAction(
    const G4Track *track) {
  if (fStopImageEnabled) {
    auto step = track->GetStep();
    AddValueToImage(track->GetStep());
  }
}

void GateProductionAndStoppingActor::AddValueToImage(const G4Step *step) {
  auto preGlobal = step->GetPreStepPoint()->GetPosition();
  auto postGlobal = step->GetPostStepPoint()->GetPosition();
  auto touchable = step->GetPreStepPoint()->GetTouchable();

  // consider random position between pre and post
  auto position = postGlobal;
  if (fHitType == "pre") {
    position = preGlobal;
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
  ImageType::PointType point;
  point[0] = localPosition[0];
  point[1] = localPosition[1];
  point[2] = localPosition[2];

  // get pixel index
  ImageType::IndexType index;
  bool isInside = cpp_value_image->TransformPhysicalPointToIndex(point, index);

  // set value
  if (isInside) {
    auto w = step->GetTrack()->GetWeight();
    {
      G4AutoLock mutex(&SetProdStopPixelMutex);
      ImageAddValue<ImageType>(cpp_value_image, index, w);
    }
  } // else : outside the image
  // else {
  // G4cout << "Outside image" << G4endl;
  //}
}
