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
#include "GateTLEDoseActor.h"

#include <iostream>
#include <itkAddImageFilter.h>
#include <itkImageRegionIterator.h>
#include <vector>

GateTLEDoseActor::GateTLEDoseActor(py::dict &user_info)
    : GateDoseActor(user_info) {
  // FIXME WARNING : not checked for MT
  fVoxelVolume = 0;
  fVoxelVolume = 0;
  fMaterialMuHandler = GateMaterialMuHandler::GetInstance();
}

void GateTLEDoseActor::InitializeUserInput(py::dict &user_info) {
  GateDoseActor::InitializeUserInput(user_info);
  fEnergyMin = py::cast<double>(user_info["energy_min"]);
}

void GateTLEDoseActor::InitializeCpp() { GateDoseActor::InitializeCpp(); }

void GateTLEDoseActor::BeginOfRunActionMasterThread(int run_id) {
  GateDoseActor::BeginOfRunActionMasterThread(run_id);
}

void GateTLEDoseActor::BeginOfRunAction(const G4Run *run) {
  GateDoseActor::BeginOfRunAction(run);
  auto s = cpp_edep_image->GetSpacing();
  fVoxelVolume = s[0] * s[1] * s[2];
}

void GateTLEDoseActor::BeginOfEventAction(const G4Event *event) {
  GateDoseActor::BeginOfEventAction(event);
}

void GateTLEDoseActor::SteppingAction(G4Step *step) {
  // Ignore non-gamma particle
  if (step->GetTrack()->GetDefinition()->GetParticleName() != "gamma")
    return;

  auto pre_step = step->GetPreStepPoint();
  double step_length = step->GetStepLength();
  double energy = pre_step->GetKineticEnergy();
  auto density = pre_step->GetMaterial()->GetDensity();
  double mu_en_over_rho = fMaterialMuHandler->GetMuEnOverRho(
      pre_step->GetMaterialCutsCouple(), energy);
  // (0.1 because length is in mm -> cm)
  double edep = 0.1 * energy * mu_en_over_rho * step_length * density /
                (CLHEP::g / CLHEP::cm3);
  if (energy <= fEnergyMin) {
    edep = energy;
    step->GetTrack()->SetTrackStatus(fStopAndKill);
  }
  double dose = edep / density;

  // Get the voxel index
  G4ThreeVector position;
  bool isInside;
  Image3DType::IndexType index;
  GetVoxelPosition(step, position, isInside, index);

  if (!isInside)
    return;

  if (fDoseFlag) {
    ImageAddValue<Image3DType>(cpp_dose_image, index, dose);
  }
  ImageAddValue<Image3DType>(cpp_edep_image, index, edep);
}

void GateTLEDoseActor::EndOfRunAction(const G4Run *run) {
  GateDoseActor::EndOfRunAction(run);
}

int GateTLEDoseActor::EndOfRunActionMasterThread(int run_id) {
  return GateDoseActor::EndOfRunActionMasterThread(run_id);
}
