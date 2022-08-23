/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateDoseActor.h"
#include "G4Navigator.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

// Mutex that will be used by thread to write in the edep/dose image
G4Mutex SetPixelMutex = G4MUTEX_INITIALIZER;

GateDoseActor::GateDoseActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  // Create the image pointer
  // (the size and allocation will be performed on the py side)
  cpp_edep_image = ImageType::New();
  // Action for this actor: during stepping
  fActions.insert("SteppingAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("EndSimulationAction");
  // Option: compute uncertainty
  fUncertaintyFlag = DictGetBool(user_info, "uncertainty");
  // Option: compute dose in Gray
  fGrayFlag = DictGetBool(user_info, "gray");
  // translation
  fInitialTranslation = DictGetG4ThreeVector(user_info, "translation");
  // Hit type (random, pre, post etc)
  fHitType = DictGetStr(user_info, "hit_type");
}

void GateDoseActor::ActorInitialize() {
  if (fUncertaintyFlag) {
    cpp_square_image = ImageType::New();
    cpp_temp_image = ImageType::New();
    cpp_last_id_image = ImageType::New();
  }
  if (fGrayFlag) {
    cpp_dose_image = ImageType::New();
  }
}

void GateDoseActor::BeginOfRunAction(const G4Run *) {
  // Important ! The volume may have moved, so we re-attach each run
  AttachImageToVolume<ImageType>(cpp_edep_image, fPhysicalVolumeName,
                                 fInitialTranslation);
  // compute volume of a dose voxel
  auto sp = cpp_edep_image->GetSpacing();
  fVoxelVolume = sp[0] * sp[1] * sp[2];
}

void GateDoseActor::SteppingAction(G4Step *step) {
  auto preGlobal = step->GetPreStepPoint()->GetPosition();
  auto postGlobal = step->GetPostStepPoint()->GetPosition();
  auto touchable = step->GetPreStepPoint()->GetTouchable();

  // FIXME If the volume has multiple copy, touchable->GetCopyNumber(0) ?

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

  // get edep in MeV (take weight into account)
  auto w = step->GetTrack()->GetWeight();
  auto edep = step->GetTotalEnergyDeposit() / CLHEP::MeV * w;

  // get pixel index
  ImageType::IndexType index;
  bool isInside = cpp_edep_image->TransformPhysicalPointToIndex(point, index);

  // set value
  if (isInside) {
    // With mutex (thread)
    G4AutoLock mutex(&SetPixelMutex);

    // If uncertainty: consider edep per event
    if (fUncertaintyFlag) {
      auto event_id =
          G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
      auto previous_id = cpp_last_id_image->GetPixel(index);
      cpp_last_id_image->SetPixel(index, event_id);
      if (event_id == previous_id) {
        // Same event : continue temporary edep
        ImageAddValue<ImageType>(cpp_temp_image, index, edep);
      } else {
        // Different event : update previous and start new event
        auto e = cpp_temp_image->GetPixel(index);
        ImageAddValue<ImageType>(cpp_edep_image, index, e);
        ImageAddValue<ImageType>(cpp_square_image, index, e * e);
        // new temp value
        cpp_temp_image->SetPixel(index, edep);
      }
    } else {
      ImageAddValue<ImageType>(cpp_edep_image, index, edep);
    }

    // Compute the dose in Gray ?
    if (fGrayFlag) {
      auto *current_material = step->GetPreStepPoint()->GetMaterial();
      auto density = current_material->GetDensity();
      auto dose = edep / density / fVoxelVolume / CLHEP::gray;
      ImageAddValue<ImageType>(cpp_dose_image, index, dose);
    }

  } // else : outside the image
}

void GateDoseActor::EndSimulationAction() {}
