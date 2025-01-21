/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "G4EmCalculator.hh"
#include "G4ParticleDefinition.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "G4Threading.hh"

#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"
#include "GateMaterialMuHandler.h"
#include "GateVoxelizedPromptGammaTLEActor.h"

#include <iostream>
#include <itkAddImageFilter.h>
#include <itkImageRegionIterator.h>
#include <vector>

GateVoxelizedPromptGammaTLEActor::GateVoxelizedPromptGammaTLEActor(
    py::dict &user_info)
    : GateVActor(user_info, false) {
  fMultiThreadReady = false;
}

void GateVoxelizedPromptGammaTLEActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  // retrieve the python param here
}

void GateVoxelizedPromptGammaTLEActor::InitializeCpp() {
  GateVActor::InitializeCpp();
  // Create the image pointers
  // (the size and allocation will be performed on the py side)
  cpp_image = ImageType::New();
}

void GateVoxelizedPromptGammaTLEActor::BeginOfRunActionMasterThread(
    int run_id) {
  std::cout << "Begin of run " << run_id << std::endl;
  std::cout << "Image size " << cpp_image->GetLargestPossibleRegion().GetSize()
            << std::endl;
}

void GateVoxelizedPromptGammaTLEActor::BeginOfEventAction(
    const G4Event *event) {}

void GateVoxelizedPromptGammaTLEActor::PreUserTrackingAction(
    const G4Track *track) {}

void GateVoxelizedPromptGammaTLEActor::SteppingAction(G4Step *step) {
  // Get the voxel index
  G4ThreeVector position;
  bool isInside;
  ImageType::IndexType index;
  GetStepVoxelPosition<ImageType>(step, "random", cpp_image, position, isInside,
                                  index);
  // if IsInside ...
}
