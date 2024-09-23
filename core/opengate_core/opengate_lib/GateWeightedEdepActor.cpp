/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateWeightedEdepActor.h"
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

// Mutex that will be used by thread to write in the edep/dose image
G4Mutex SetWeightedPixelMutex = G4MUTEX_INITIALIZER;

G4Mutex SetWeightedNbEventMutex = G4MUTEX_INITIALIZER;

GateWeightedEdepActor::GateWeightedEdepActor(py::dict &user_info) : GateVActor(user_info, true) {
  // Action for this actor: during stepping
  fActions.insert("SteppingAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("EndSimulationAction");
}

void GateWeightedEdepActor::InitializeUserInput(py::dict &user_info) {
  // IMPORTANT: call the base class method
  GateVActor::InitializeUserInput(user_info);

  fScoreIn = DictGetStr(user_info, "score_in");
  if (fScoreIn != "material") {
    fScoreInOtherMaterial = true;
  }

  fInitialTranslation = DictGetG4ThreeVector(user_info, "translation");
  // Hit type (random, pre, post etc)
  fHitType = DictGetStr(user_info, "hit_type");
}

void GateWeightedEdepActor::InitializeCpp() {
  // Create the image pointer
  // (the size and allocation will be performed on the py side)
  cpp_numerator_image = ImageType::New();
  cpp_denominator_image = ImageType::New();
}

void GateWeightedEdepActor::BeginOfRunActionMasterThread(int run_id) {
  // Reset the number of events (per run)
  NbOfEvent = 0;

  // Important ! The volume may have moved, so we re-attach each run
  AttachImageToVolume<ImageType>(cpp_numerator_image, fPhysicalVolumeName,
                                 fInitialTranslation);
  AttachImageToVolume<ImageType>(cpp_denominator_image, fPhysicalVolumeName,
                                 fInitialTranslation);
  // compute volume of a dose voxel
  auto sp = cpp_numerator_image->GetSpacing();
  fVoxelVolume = sp[0] * sp[1] * sp[2];
}

void GateWeightedEdepActor::BeginOfRunAction(const G4Run *) {
  if (fScoreInOtherMaterial) {
    auto &l = fThreadLocalData.Get();
    l.materialToScoreIn =
        G4NistManager::Instance()->FindOrBuildMaterial(fScoreIn);
  }
}

void GateWeightedEdepActor::BeginOfEventAction(const G4Event *event) {
  G4AutoLock mutex(&SetWeightedNbEventMutex);
  NbOfEvent++;
}

void GateWeightedEdepActor::SteppingAction(G4Step *step) {

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

  // get pixel index
  ImageType::IndexType index;
  bool isInside =
      cpp_numerator_image->TransformPhysicalPointToIndex(point, index);

  // set value
  if (isInside) {
    // With mutex (thread)
    G4AutoLock mutex(&SetWeightedPixelMutex);
    // Call the function implemented by the children class
    AddValuesToImages(step, index);
  } // else : outside the image
}

void GateWeightedEdepActor::AddValuesToImages(G4Step *step,ImageType::IndexType index){}

void GateWeightedEdepActor::EndSimulationAction() {}
