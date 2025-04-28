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
   #include"G4Gamma.hh"
   
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
   
    GateVoxelizedPromptGammaTLEActor::~GateVoxelizedPromptGammaTLEActor() {
      // Destructor
      cpp_image = nullptr;
    }

   void GateVoxelizedPromptGammaTLEActor::InitializeUserInfo(py::dict &user_info) {
     GateVActor::InitializeUserInfo(user_info);
     // retrieve the python param here
     bins = py::int_(user_info["bins"]);
     range = py::float_(user_info["range"]);
     prot = py::bool_(user_info["proton"]);
     std::cout<< bins << range << std::endl;
     std::cout<<"particle of interest is proton : " << prot << std::endl;

   }
   
   void GateVoxelizedPromptGammaTLEActor::InitializeCpp() {
     GateVActor::InitializeCpp();
     // Create the image pointers
     // (the size and allocation will be performed on the py side)
     cpp_image = ImageType::New();
     norm = 0 ;
     incidentParticles = 0;
   }
   
   void GateVoxelizedPromptGammaTLEActor::BeginOfRunActionMasterThread(
       int run_id) {
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
     GetStepVoxelPosition<ImageType>(step, "random", cpp_image, position, isInside,
                                     index);
      if(!isInside) {
       return; // Skip if not inside the volume
      }
      // Get the particle type
      if((step->GetTrack()->GetParticleDefinition()->GetParticleName() != "proton") && prot){
        return; // Skip if not a proton and proton wanted
      }

      if((step->GetTrack()->GetParticleDefinition()->GetParticleName() != "neutron") && !prot){
        return; // Skip if not a neutron and neutron wanted
      }

      /*
      if ((step->GetTrack()->GetParentID() != 0) && (step->GetTrack()->GetCurrentStepNumber() == 1)) {
        T0 = step->GetTrack()->GetGlobalTime();
      } */

      auto sec = step->GetSecondary();
      for (size_t i = 0; i < sec->size(); i++) {
        auto secondary = sec->at(i);
        auto secondary_def = secondary->GetParticleDefinition();

        if (secondary_def != G4Gamma::Gamma()) {
          continue;
        }
        if (secondary->GetCreatorProcess()->GetProcessName() != "protonInelastic" && prot) {
          continue;
        }
        if (secondary->GetCreatorProcess()->GetProcessName() != "neutronInelastic" && !prot) {
          continue;
        }

        // Get the energy of the gamma
        G4double energyPG = secondary->GetKineticEnergy();
        // Get the time of flight
        G4double time = step->GetPostStepPoint()->GetGlobalTime() - T0;
        // Get the voxel index
        ImageType::IndexType ind;
        ind[0] = index[0];
        ind[1] = index[1];
        ind[2] = index[2];

        int bin = static_cast<int>(time / (range / bins));
        if (bin >= bins) {
          bin = bins - 1;
        }
        ind[3] = bin;
        std::cout<<"Voxel index: " << ind[0] << ", " << ind[1] << ", " << ind[2]
                 << ", " << ind[3] << " for the time : " << time << std::endl;
        if (prot){
          std::cout << "Proton inelastic collision of interest" << std::endl;
        } else {
          std::cout << "Neutron inelastic collision of interest" << std::endl;
        }
        cpp_image->SetPixel(ind, cpp_image->GetPixel(ind) + 1);
        norm = norm + 1;
      }
     }

   void GateVoxelizedPromptGammaTLEActor::EndOfRunAction(const G4Run *run) {
    itk::ImageRegionIterator<ImageType> it(
    cpp_image, cpp_image->GetLargestPossibleRegion());
    for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
      it.Set(it.Get() / norm);
    }
    std::cout << "incident proton : " << incidentParticles << std::endl;
    std::cout << "inelastic collision of interest " << norm << " for " << prot << std::endl;
    } 

   int GateVoxelizedPromptGammaTLEActor::EndOfRunActionMasterThread(int run_id) {
    return 0;
    }
