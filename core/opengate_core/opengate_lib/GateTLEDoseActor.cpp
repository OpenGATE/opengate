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

G4Mutex SetPixelTLEMutex = G4MUTEX_INITIALIZER;

GateTLEDoseActor::GateTLEDoseActor(py::dict &user_info)
    : GateDoseActor(user_info) {
  fMultiThreadReady = true;
}

void GateTLEDoseActor::InitializeUserInfo(py::dict &user_info) {
  GateDoseActor::InitializeUserInfo(user_info);
  fEnergyMin = py::cast<double>(user_info["energy_min"]);
  fEnergyMax = py::cast<double>(user_info["energy_max"]);
  auto database = py::cast<std::string>(user_info["database"]);
  fMaterialMuHandler = GateMaterialMuHandler::GetInstance(database, fEnergyMax);
}


void GateTLEDoseActor::BeginOfEventAction(const G4Event* event) {
  auto &l = fThreadLocalData.Get();
  l.fIsTLESecondary = false;
  l.fSecNbWhichDeposit.clear();
  GateDoseActor::BeginOfEventAction(event);


}
void GateTLEDoseActor::PreUserTrackingAction(const G4Track *track) {
  auto &l = fThreadLocalData.Get();


  if (track->GetDefinition()->GetParticleName() == "gamma") {
    l.fIsTLEGamma = false;
    l.fIsTLESecondary = false;
    l.fSecNbWhichDeposit[track->GetTrackID()] = 0;
  }


  //if the particle
  else {
    auto parent_id = track->GetParentID();
    //std::cout<<"begin"<<std::endl;
    for (auto it = l.fSecNbWhichDeposit.begin(); it != l.fSecNbWhichDeposit.end(); ++it) {
      //std::cout <<it->first<<"  "<<it->second<<std::endl;
        if (parent_id  == it->first){
          if (it->second > 0){
            l.fIsTLESecondary = true;
          }
          if (it->second == 0){
            l.fSecNbWhichDeposit.erase(it);
            l.fIsTLESecondary = false;
            break;
          }
          it->second --;
        }
    }
    //std::cout<<"end"<<std::endl;
  }
}


void GateTLEDoseActor::SteppingAction(G4Step *step) {
  auto &l = fThreadLocalData.Get();

  auto pre_step = step->GetPreStepPoint();
  double energy = 0;
  if (pre_step !=0)
    energy =pre_step->GetKineticEnergy();
  if (step->GetTrack()->GetDefinition()->GetParticleName() == "gamma") {

  // For too high energy, no TLE
    if (energy > fEnergyMax) {
      l.fIsTLEGamma = false;
      l.fIsTLESecondary = false;
      return GateDoseActor::SteppingAction(step);
   }
    else {
      l.fIsTLEGamma = true;
    }
  // Update the number of secondaries if there is secondary in the current non TLE particle
    if (l.fIsTLEGamma==true){
      auto nbSec = step->GetSecondaryInCurrentStep()->size();
      if (nbSec > 0){
        l.fIsTLESecondary = true;
        l.fSecNbWhichDeposit[step->GetTrack()->GetTrackID()] += nbSec;
      }
      //l.fLastTrackId += step->GetSecondaryInCurrentStep()->size();
    }
  }



  // For non-gamma particle, no TLE
  if (step->GetTrack()->GetDefinition()->GetParticleName() != "gamma") {
    if (l.fIsTLESecondary == true){
      return;
    }
    return GateDoseActor::SteppingAction(step);
  }


  auto weight = step->GetTrack()->GetWeight();
  auto step_length = step->GetStepLength();
  auto density = pre_step->GetMaterial()->GetDensity();
  auto mu_en_over_rho = fMaterialMuHandler->GetMuEnOverRho(
      pre_step->GetMaterialCutsCouple(), energy);
  // (0.1 because length is in mm -> cm)
  auto edep = weight * 0.1 * energy * mu_en_over_rho * step_length * density /
              (CLHEP::g / CLHEP::cm3);

  // Kill photon below a given energy
  if (energy <= fEnergyMin) {
    edep = energy;
    step->GetTrack()->SetTrackStatus(fStopAndKill);
  }
  double dose = edep / density;

  // Get the voxel index and check if the step was within the 3D image
  G4ThreeVector position;
  bool isInside;
  Image3DType::IndexType index;
  GetVoxelPosition(step, position, isInside, index);
  auto event_id =
      G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
  if (isInside) {
    G4AutoLock mutex(&SetPixelTLEMutex); // mutex is bound to the if-scope
    if (fDoseFlag) {
      ImageAddValue<Image3DType>(cpp_dose_image, index, dose);
    }
    ImageAddValue<Image3DType>(cpp_edep_image, index, edep);

    if (fEdepSquaredFlag || fDoseSquaredFlag) {
      if (fEdepSquaredFlag) {
        ScoreSquaredValue(fThreadLocalDataEdep.Get(), cpp_edep_squared_image,
                          edep, event_id, index);
      }
      if (fDoseSquaredFlag) {
        ScoreSquaredValue(fThreadLocalDataDose.Get(), cpp_dose_squared_image,
                          dose, event_id, index);
      }
    }
  }
}
