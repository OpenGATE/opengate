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
   #include "GateVoxelizedPromptGammaAnalogActor.h"
   
   #include "CLHEP/Random/Randomize.h"
   #include <iostream>
   #include <itkAddImageFilter.h>
   #include <itkCastImageFilter.h>
   #include <itkImageRegionIterator.h>
   #include <vector>
   
   #include <G4Proton.hh>
   #include <G4VProcess.hh>
   //#include <G4ProtonInelasticProcess.hh>
   #include <G4CrossSectionDataStore.hh>
   #include <G4HadronicProcessStore.hh>

   GateVoxelizedPromptGammaAnalogActor::GateVoxelizedPromptGammaAnalogActor(
       py::dict &user_info)
       : GateVActor(user_info, true) {
     fMultiThreadReady =
         true; // But used as a single thread python side : nb pf runs = 1
   }
   
   GateVoxelizedPromptGammaAnalogActor::~GateVoxelizedPromptGammaAnalogActor() {
     // not needed
     cpp_tof_proton_image = nullptr;
     cpp_E_proton_image = nullptr;
     cpp_E_neutron_image = nullptr;
     cpp_tof_neutron_image = nullptr;
   
     // Release the 3D volume
     volume = nullptr;
     std::cout << "GateVoxelizedPromptGammaAnalogActor destructor called. "
                  "Resources released."
               << std::endl;
   }
   
   void GateVoxelizedPromptGammaAnalogActor::InitializeUserInfo(
       py::dict &user_info) {
     GateVActor::InitializeUserInfo(user_info);
   
     // retrieve the python param here
     timebins = py::int_(user_info["timebins"]);
     timerange = py::float_(user_info["timerange"]);
     energybins = py::int_(user_info["energybins"]);
     energyrange = py::float_(user_info["energyrange"]);
   
     fTranslation = DictGetG4ThreeVector(user_info, "translation");
     fsize = DictGetG4ThreeVector(user_info, "size");
     fspacing = DictGetG4ThreeVector(user_info, "spacing");
   }
   
   void GateVoxelizedPromptGammaAnalogActor::InitializeCpp() {
     GateVActor::InitializeCpp();
     // Create the image pointers
     // (the size and allocation will be performed on the py side)
     if (fProtonTimeFlag) {
       cpp_tof_proton_image = ImageType::New();
     }
     if (fProtonEnergyFlag) {
       cpp_E_proton_image = ImageType::New();
     }
     if (fNeutronEnergyFlag) {
       cpp_E_neutron_image = ImageType::New();
     }
     if (fNeutronTimeFlag) {
       cpp_tof_neutron_image = ImageType::New();
     }
   
     // Construction of the 3D image with the same shape/mat that the voxel of the
     // actor but is accepted by the method of volume_attach and "isInside"
     volume = Image3DType::New();
   
     Image3DType::RegionType region;
     Image3DType::SizeType size;
     Image3DType::SpacingType spacing;
   
     size[0] = fsize[0];
     size[1] = fsize[1];
     size[2] = fsize[2];
     region.SetSize(size);
   
     spacing[0] = fspacing[0];
     spacing[1] = fspacing[1];
     spacing[2] = fspacing[2];
   
     volume->SetRegions(region);
     volume->SetSpacing(spacing);
     volume->Allocate();
     volume->FillBuffer(0);
   
     incidentParticles =
         0; // initiate the conuter of incidente protons - scaling factor
   }
   
   void GateVoxelizedPromptGammaAnalogActor::BeginOfRunActionMasterThread(
       int run_id) {
     // Attach the 3D volume used to
   
     // Fill the 4D volume of interest with 0 to ensure that it is well initiated
     if (fProtonTimeFlag) {
       cpp_tof_proton_image->FillBuffer(0);
     }
     if (fProtonEnergyFlag) {
       cpp_E_proton_image->FillBuffer(0);
     }
     if (fNeutronEnergyFlag) {
       cpp_E_neutron_image->FillBuffer(0);
     }
     if (fNeutronTimeFlag) {
       cpp_tof_neutron_image->FillBuffer(0);
     }
     AttachImageToVolume<Image3DType>(volume, fPhysicalVolumeName, fTranslation);
   }
   
   void GateVoxelizedPromptGammaAnalogActor::BeginOfRunAction(const G4Run *run) {}
   
   void GateVoxelizedPromptGammaAnalogActor::BeginOfEventAction(
       const G4Event *event) {
     T0 = event->GetPrimaryVertex()->GetT0();
     incidentParticles++;
   }
   
   void GateVoxelizedPromptGammaAnalogActor::SteppingAction(G4Step *step) {
     if (step->GetTrack()->GetParticleDefinition() != G4Neutron::Neutron()
              &&
         (step->GetTrack()->GetParticleDefinition() != G4Proton::Proton())) {
       return;
     }
     static G4HadronicProcessStore* store = G4HadronicProcessStore::Instance();
     static G4VProcess * protonInelastic = store->FindProcess(G4Proton::Proton(), fHadronInelastic);
     static G4VProcess * neutronInelastic = store->FindProcess(G4Neutron::Neutron(), fHadronInelastic);
     if (step->GetPostStepPoint()->GetProcessDefinedStep() != protonInelastic &&
         step->GetPostStepPoint()->GetProcessDefinedStep() != neutronInelastic) {
       return;
     }

     auto position = step->GetPostStepPoint()->GetPosition();
     auto touchable = step->GetPreStepPoint()->GetTouchable();
     // Get the voxel index
     auto localPosition =
         touchable->GetHistory()->GetTransform(0).TransformPoint(position);
   
     // convert G4ThreeVector to itk PointType
     Image3DType::PointType point;
     point[0] = localPosition[0];
     point[1] = localPosition[1];
     point[2] = localPosition[2];
   
     Image3DType::IndexType index;
     G4bool isInside = volume->TransformPhysicalPointToIndex(point, index);
     if (!isInside) { // verification
       return;        // Skip if not inside the volume
     }
   
     // Get the spatial index from the index obtained with the 3D volume and th
     // emethod GetStepVoxelPosition()
     ImageType::IndexType ind;
     ind[0] = index[0];
     ind[1] = index[1];
     ind[2] = index[2];
   
     auto secondaries = step->GetSecondary();
     for (size_t i = 0; i < secondaries->size(); i++) {
       auto secondary = secondaries->at(i);
       auto secondary_def = secondary->GetParticleDefinition();
       if (secondary_def != G4Gamma::Gamma()) {
         continue;
       }
       G4double gammaEnergy = secondary->GetKineticEnergy(); // in MeV
       // thershold with a minimum energy of 40 keV
       if (gammaEnergy < 0.04 * CLHEP::MeV) {
         continue;
       }
   
       if (fProtonTimeFlag ||
           fNeutronTimeFlag) { // If the quantity of interest is the time of flight
         // Get the time of flight
         // G4double randomtime = G4UniformRand();
         // G4double pretime = step->GetPreStepPoint()->GetGlobalTime()- T0; //ns
         // G4double posttime = step->GetPostStepPoint()->GetGlobalTime()- T0;//ns
         G4double time = secondary->GetGlobalTime() - T0; // ns
   
         // Get the voxel index (fourth dim) corresponding to the time of flight
         G4int bin = static_cast<int>(
             time / (timerange / timebins)); // Always the left bin
   
         if (bin >= timebins) {
           bin = timebins;
         }
         ind[3] = bin;
         // Store the value in the volume for neutrons OR protons -> LEFT BINNING
         if (fProtonTimeFlag &&
             step->GetTrack()->GetParticleDefinition()->GetParticleName() ==
                 "proton") {
           ImageAddValue<ImageType>(cpp_tof_proton_image, ind, 1);
         }
         if (fNeutronTimeFlag &&
             step->GetTrack()->GetParticleDefinition()->GetParticleName() ==
                 "neutron") {
           ImageAddValue<ImageType>(cpp_tof_neutron_image, ind, 1);
         }
       }
       if (fProtonEnergyFlag ||
           fNeutronEnergyFlag) { // when the quantity of interest is the energy
         // Get the voxel index (fourth dim) corresponding to the energy of the
         // projectile
         G4int bin = static_cast<int>(
             gammaEnergy / (energyrange / energybins)); // Always the left bin
         if (bin >= energybins) {
           bin = energybins;
         }
         if (bin < 0) {
           bin = 0; // underflow
         }
         ind[3] = bin;
         // Store the value in the volume for neutrons OR protons -> LEFT BINNING
         if (fProtonEnergyFlag &&
             step->GetTrack()->GetParticleDefinition()->GetParticleName() ==
                 "proton") {
           ImageAddValue<ImageType>(cpp_E_proton_image, ind, 1);
         }
         if (fNeutronEnergyFlag &&
             step->GetTrack()->GetParticleDefinition()->GetParticleName() ==
                 "neutron") {
           ImageAddValue<ImageType>(cpp_E_neutron_image, ind, 1);
         }
       }
     }
   }
   
   void GateVoxelizedPromptGammaAnalogActor::EndOfRunAction(const G4Run *run) {
     std::cout << "incident particles : " << incidentParticles << std::endl;
     if (incidentParticles == 0) {
       std::cerr << "Error: incidentParticles is zero. Skipping scaling."
                 << std::endl;
       return;
     }
     // scaling all the 4D voxels with th enumber of incident protons (= number of
     // event)
     if (fProtonTimeFlag) {
       itk::ImageRegionIterator<ImageType> it(
           cpp_tof_proton_image, cpp_tof_proton_image->GetLargestPossibleRegion());
       for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
         it.Set(it.Get() / incidentParticles);
       }
     }
     if (fProtonEnergyFlag) {
       itk::ImageRegionIterator<ImageType> it(
           cpp_E_proton_image, cpp_E_proton_image->GetLargestPossibleRegion());
       for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
         it.Set(it.Get() / incidentParticles);
       }
     }
     if (fNeutronEnergyFlag) {
       itk::ImageRegionIterator<ImageType> it(
           cpp_E_neutron_image, cpp_E_neutron_image->GetLargestPossibleRegion());
       for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
         it.Set(it.Get() / incidentParticles);
       }
     }
     if (fNeutronTimeFlag) {
       itk::ImageRegionIterator<ImageType> it(
           cpp_tof_neutron_image,
           cpp_tof_neutron_image->GetLargestPossibleRegion());
       for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
         it.Set(it.Get() / incidentParticles);
       }
     }
   }
   
   int GateVoxelizedPromptGammaAnalogActor::EndOfRunActionMasterThread(
       int run_id) {
     return 0;
   }