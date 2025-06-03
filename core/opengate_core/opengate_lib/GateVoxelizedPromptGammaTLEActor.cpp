/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */


#include "G4EmCalculator.hh"
#include "G4Gamma.hh"
#include "G4ParticleDefinition.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "G4Threading.hh"
#include "G4Track.hh"

#include "G4HadronInelasticProcess.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"
#include "GateMaterialMuHandler.h"
#include "GateVoxelizedPromptGammaTLEActor.h"

#include <iostream>
#include <itkAddImageFilter.h>
#include <itkCastImageFilter.h>
#include <itkImageRegionIterator.h>
#include <vector>
#include "CLHEP/Random/Randomize.h" 

GateVoxelizedPromptGammaTLEActor::GateVoxelizedPromptGammaTLEActor(
    py::dict &user_info)
    : GateVActor(user_info, true) {
  fMultiThreadReady = true;
}

GateVoxelizedPromptGammaTLEActor::~GateVoxelizedPromptGammaTLEActor() {
  cpp_tof_proton_image = nullptr;
  cpp_tof_neutron_image = nullptr;
  cpp_E_proton_image = nullptr;
  cpp_E_neutron_image = nullptr;

  std::cout << "ITK images destroyed in destructor." << std::endl;
}

void GateVoxelizedPromptGammaTLEActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  // retrieve the python param here
  bins = py::int_(user_info["bins"]);
  range = py::float_(user_info["range"]);
  prot = py::bool_(user_info["proton"]);
  energy = py::bool_(user_info["energy"]);
  std::cout << bins << range << std::endl;
  std::cout << "particle of interest is proton : " << prot << std::endl;
  std::cout << "the quantity of interest is energy : " << energy << std::endl;
}

void GateVoxelizedPromptGammaTLEActor::InitializeCpp() {
  GateVActor::InitializeCpp();
  // Create the image pointers
  // (the size and allocation will be performed on the py side)
  if(!prot){
    if(!energy){
      cpp_tof_neutron_image = ImageType::New();
      cpp_tof_proton_image = nullptr;
      cpp_E_neutron_image = nullptr;
      cpp_E_proton_image = nullptr;
    }else{
      cpp_tof_neutron_image = nullptr;
      cpp_tof_proton_image = nullptr;
      cpp_E_neutron_image = ImageType::New();
      cpp_E_proton_image = nullptr;
    }
  }else{
    if (!energy){
      cpp_tof_neutron_image = nullptr;
      cpp_tof_proton_image = ImageType::New();
      cpp_E_neutron_image = nullptr;
      cpp_E_proton_image = nullptr;
    }else{
      cpp_tof_neutron_image = nullptr;
      cpp_tof_proton_image = nullptr;
      cpp_E_neutron_image = nullptr;
      cpp_E_proton_image = ImageType::New();
    }
  }
  incidentParticles = 1;
}

void GateVoxelizedPromptGammaTLEActor::BeginOfRunActionMasterThread(
    int run_id) {
    if(prot){
      if(energy){
        cpp_E_proton_image->FillBuffer(0);
      }else{
        cpp_tof_proton_image->FillBuffer(0);
      }
    }else{
      if(energy){
        cpp_E_neutron_image->FillBuffer(0);
      }else{
        cpp_tof_neutron_image->FillBuffer(0);
      }
    }
  }

void GateVoxelizedPromptGammaTLEActor::BeginOfEventAction(
    const G4Event *event) {
  T0 = event->GetPrimaryVertex()->GetT0();
  incidentParticles++;
}

void GateVoxelizedPromptGammaTLEActor::SteppingAction(G4Step *step) {
  // Get the voxel index
  
  G4ThreeVector position;
  bool isInside;
  ImageType::IndexType index;
  if(prot){
    if(!energy){
      GetStepVoxelPosition<ImageType>(step, "random", cpp_tof_proton_image, position, isInside,
                                  index);
    }else{GetStepVoxelPosition<ImageType>(step, "random", cpp_E_proton_image, position, isInside,
                                  index);}
  }else{
    if(!energy){
      GetStepVoxelPosition<ImageType>(step, "random", cpp_tof_neutron_image, position, isInside,
                                  index);
    }else{GetStepVoxelPosition<ImageType>(step, "random", cpp_E_neutron_image, position, isInside,
                                  index);}
  }
  
  if (!isInside) {
    return; // Skip if not inside the volume
  }
  // Get the particle typecd
  if ((step->GetTrack()->GetParticleDefinition()->GetParticleName() !=
       "proton") &&
      prot) {
    return; // Skip if not a proton and proton wanted
  }

  if ((step->GetTrack()->GetParticleDefinition()->GetParticleName() !=
       "neutron") &&
      !prot) {
    return; // Skip if not a neutron and neutron wanted
  }


  auto sec = step->GetSecondary();
  for (size_t i = 0; i < sec->size(); i++) {
    auto secondary = sec->at(i);
    auto secondary_def = secondary->GetParticleDefinition();

    if (secondary_def != G4Gamma::Gamma()) {
      continue;
    }
    if (secondary->GetCreatorProcess()->GetProcessName() != "protonInelastic" &&
        prot) {
      continue;
    }
    if (secondary->GetCreatorProcess()->GetProcessName() != "neutronInelastic" &&
        !prot) {
      continue;
    }
    G4double w = step->GetTrack()->GetWeight();
    ImageType::IndexType ind;
    ind[0] = index[0];
    ind[1] = index[1];
    ind[2] = index[2];
    int bin = 0;
    if(!energy){
    // Get the time of flight
      G4double pretime = step->GetPreStepPoint()->GetGlobalTime();
      G4double posttime = step->GetPostStepPoint()->GetGlobalTime();
      G4double time = (pretime + G4UniformRand() * (posttime - pretime)) - T0;
      if (time > range){
        continue;
      }
    // Get the voxel index
      bin = static_cast<int>(time / (range / bins));
      if (bin == bins) {
        bin = bins - 1;
      }
      ind[3] = bin;
      if (prot) {
        ImageAddValue<ImageType>(cpp_tof_proton_image, ind, w);
      } else {
        ImageAddValue<ImageType>(cpp_tof_neutron_image, ind, w);
      }
    }else{
      G4double postE = step->GetPostStepPoint()->GetKineticEnergy();
      G4double preE = step->GetPreStepPoint()->GetKineticEnergy();
      G4double projectileEnergy = preE + G4UniformRand() * (postE - preE);
      if (projectileEnergy > range) {
        continue; // Skip if energy is out of range
      }
      bin = static_cast<int>(projectileEnergy / (range / bins));
      if (bin == bins) {
        bin = bins - 1;
      }
      ind[3] = bin; 
      std::cout << "Voxel index: " << ind[0] << ", " << ind[1] << ", " << ind[2]
              << ", " << ind[3] <<  std::endl;
      G4double l = step->GetStepLength();
      G4Material *mat = step->GetPreStepPoint()->GetMaterial();
      G4double rho = mat->GetDensity() / (CLHEP::g / CLHEP::cm3); // Convert to g/cm3
      if (prot) {
        ImageAddValue<ImageType>(cpp_E_proton_image, ind, rho * w * l);
      } else {
        ImageAddValue<ImageType>(cpp_E_neutron_image, ind,rho * w * l);
      }
    }
  }
}

void GateVoxelizedPromptGammaTLEActor::EndOfRunAction(const G4Run *run) {
  std::cout << "incident proton : " << incidentParticles << std::endl;
  if(prot){
    if(!energy){
      itk::ImageRegionIterator<ImageType> it(cpp_tof_proton_image,cpp_tof_proton_image->GetLargestPossibleRegion());
      for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
        it.Set(it.Get() / incidentParticles);
      }
    }else{
      itk::ImageRegionIterator<ImageType> it(cpp_E_proton_image,cpp_E_proton_image->GetLargestPossibleRegion());
      for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
        it.Set(it.Get() / incidentParticles);
      }
    }
    }else{
      if(!energy){
        itk::ImageRegionIterator<ImageType> it(cpp_tof_neutron_image, cpp_tof_neutron_image->GetLargestPossibleRegion());
        for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
          it.Set(it.Get() / incidentParticles);}
      }else{
        itk::ImageRegionIterator<ImageType> it(cpp_E_neutron_image, cpp_E_neutron_image->GetLargestPossibleRegion());
        for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
          it.Set(it.Get() / incidentParticles);
        }
      }
    }
  }

int GateVoxelizedPromptGammaTLEActor::EndOfRunActionMasterThread(int run_id) {
  return 0;
}
