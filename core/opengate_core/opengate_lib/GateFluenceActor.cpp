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
   #include "G4Gamma.hh"
   #include "G4Track.hh"
   
   #include "GateHelpers.h"
   #include "GateHelpersDict.h"
   #include "GateHelpersImage.h"
   #include "GateMaterialMuHandler.h"
   #include "GateFluenceActor.h"
   #include "G4HadronInelasticProcess.hh"
   
   
   #include <iostream>
   #include <itkAddImageFilter.h>
   #include <itkImageRegionIterator.h>
   #include <itkImageFileWriter.h>
   #include <itkCastImageFilter.h>
   #include <vector>
   


GateFluenceActor::GateFluenceActor(py::dict &user_info)
   : GateVActor(user_info, true) {  
    fMultiThreadReady = true;}

void GateFluenceActor::InitializeUserInfo(py::dict &user_info) {
  // IMPORTANT: call the base class method
  GateVActor::InitializeUserInfo(user_info);
  fTranslation = DictGetG4ThreeVector(user_info,"translation");
  fsize = DictGetG4ThreeVector(user_info,"size");
  fspacing = DictGetG4ThreeVector(user_info,"spacing");
  Nbbinstime = py::int_(user_info["timebins"]);
  Nbbinsenergy = py::int_(user_info["energybins"]);
  foutputname = std::string(py::str(user_info["output_name"]));
}

void GateFluenceActor::InitializeCpp() {
  GateVActor::InitializeCpp();
  // Create the image pointers
  // (the size and allocation will be performed on the py side)
  tof_cpp_image = Image3DType::New();

  Image3DType::RegionType region3;
  Image3DType::SizeType size3;
  size3[0] = fsize[0]; // Replace with actual size in X
  size3[1] = fsize[1]; // Replace with actual size in Y
  size3[2] = fsize[2]; // Replace with actual size in Z
  region3.SetSize(size3);
  
  Image3DType::SpacingType spacing3;
  spacing3[0] = fspacing[0]; // Replace with actual spacing in X
  spacing3[1] = fspacing[1]; // Replace with actual spacing in Y
  spacing3[2] = fspacing[2]; // Replace with actual spacing in Z
  
  Image3DType::PointType origin;
  origin[0] = fTranslation[0]; // Replace with actual origin in X
  origin[1] = fTranslation[1]; // Replace with actual origin in Y
  origin[2] = fTranslation[2]; // Replace with actual origin in Z
  
  tof_cpp_image->SetRegions(region3);
  tof_cpp_image->SetSpacing(spacing3);
  tof_cpp_image->SetOrigin(origin);
  tof_cpp_image->Allocate();
  tof_cpp_image->FillBuffer(0);


  output_image = Image2DType::New();
  

  Image2DType::RegionType region;
  Image2DType::SizeType size;
  size[0] = Nbbinsenergy; // Width
  size[1] = Nbbinstime;  // Height
  region.SetSize(size);

  Image2DType::SpacingType spacing;
  spacing[0] = 1.0; // Energy spacing
  spacing[1] = 1.0; // Time spacing

  output_image->SetRegions(region);
  output_image->SetSpacing(spacing);
  output_image->Allocate();
  output_image->FillBuffer(0); // Initialize with zeros

  norm = 0;
  nb_inel = 0;
}

void GateFluenceActor::BeginOfEventAction(const G4Event *event) {
}

void GateFluenceActor::BeginOfRunActionMasterThread(int run_id) {
  // Important ! The volume may have moved, so we (re-)attach each run
  AttachImageToVolume<Image3DType>(tof_cpp_image, fPhysicalVolumeName, fTranslation);
}

void GateFluenceActor::SteppingAction(G4Step *step) {
   // Get the voxel index
  if (step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName() == "neutronInelastic" || step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName() == "protonInelastic"){
    nb_inel = nb_inel + 1; 
  }
  if (step->GetTrack()->GetParticleDefinition()->GetParticleName() != "proton"){
    return;
  }
  auto secondaries = step->GetSecondary();
  for (size_t i = 0; i < secondaries->size(); i++) {
    auto secondary = secondaries->at(i);
    auto secondary_def = secondary->GetParticleDefinition();

    if (secondary_def != G4Gamma::Gamma()) {
      continue;
    }
    if (secondary->GetCreatorProcess()->GetProcessName() != "protonInelastic") {
      continue;
    }

     // Get the position of the interaction
    //auto preposition = step->GetPreStepPoint()->GetPosition();
    auto position = step->GetPostStepPoint()->GetPosition();
    auto touchable = step->GetPreStepPoint()->GetTouchable();

      // Get the voxel index
    auto localPosition = touchable->GetHistory()->GetTransform(0).TransformPoint(position);
      // convert G4ThreeVector to itk PointType
    Image3DType::PointType point;
    point[0] = localPosition[0];
    point[1] = localPosition[1];
    point[2] = localPosition[2];

    Image3DType::IndexType index;
    G4bool isInside = tof_cpp_image->TransformPhysicalPointToIndex(point, index);

    if (!isInside) {
      return;
    } 

    auto energyPG = secondary->GetKineticEnergy(); // Get the energy of the secondary

    if (energyPG < 0) {
      std::cerr << "Warning: Negative energy detected." << std::endl;
      continue;
    }

    G4double energy_range_EP = 10.0 * CLHEP::MeV ;  // Replace with the actual range of energy values

    Image2DType::IndexType ind;
    G4double widthbin =(energy_range_EP/Nbbinsenergy);
    
        // Assign bin for time (ind[1])
    ind[0] = static_cast<int>(energyPG / widthbin);
    if (ind[0] >= Nbbinsenergy) {
        ind[0] = Nbbinsenergy - 1;  // Clamp to the maximum bin index
      }
  
        // Clamp energyPG to the valid range
    if (energyPG < 0) energyPG = 0;
    if (energyPG > energy_range_EP) energyPG = energy_range_EP;
        
    //time of the fragmentation : 
    creationtime = step->GetPostStepPoint()->GetGlobalTime();

    //time of the gamma emission
    G4double currenttime = secondary->GetGlobalTime();

    //time of emission
    G4double time = (currenttime - creationtime) * 1e6; //fs 
    
    if (time == 0) {
      continue;
    }

    std::cout << "Current time: " << currenttime << std::endl;
    std::cout << "Creation time: " << creationtime << std::endl;
    std::cout << "Time: " << time << std::endl;

    
    G4double time_max =  1e6; 
    G4double time_min = 1;  // to avoid log(0))
    G4double log_time_min = std::log(time_min);
    G4double log_time_max = std::log(time_max);
    G4double log_time_width = (log_time_max - log_time_min) / Nbbinstime;

    // Assign bin for time (log scale)
    if (time < time_min) time = time_min;
    if (time > time_max) time = time_max;
    ind[1] = static_cast<int>((std::log(time) - log_time_min) / log_time_width);
    if (ind[1] >= Nbbinstime) ind[1] = Nbbinstime - 1;  // Sécurité

    norm = norm + 1;
    std::cout << "Voxel index: " << ind[0] << ", " << ind[1] << std::endl;
    ImageAddValue<Image2DType>(output_image, ind, 1);
  }
}



void GateFluenceActor::EndOfRunAction(const G4Run *run){
  /*
  itk::ImageRegionIterator<Image2DType> it(output_image,output_image->GetLargestPossibleRegion());
  for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
    it.Set(it.Get() / norm);
  }*/
  std::cout<<"neutroninel"<<norm<<std::endl;
  std::cout<<"desexcitation"<<nb_inel<<std::endl;
  std::cout<<"proba"<<(norm/nb_inel)*100<<std::endl;
}

std::string GateFluenceActor::GetOutputImage() {

  using InputImageType = itk::Image<double, 2>;
  using OutputImageType = itk::Image<float, 2>;
  using CastFilterType = itk::CastImageFilter<InputImageType, OutputImageType>;

  try {
    auto castFilter = CastFilterType::New();
    castFilter->SetInput(output_image);
    castFilter->Update();

    using WriterType = itk::ImageFileWriter<OutputImageType>;
    auto writer = WriterType::New();
    writer->SetFileName(foutputname);
    writer->SetInput(castFilter->GetOutput());
    writer->Update();
  } catch (const itk::ExceptionObject &e) {
    std::cerr << "Error during ITK operations: " << e << std::endl;
    throw;
  }
  return foutputname; 
}

  
int GateFluenceActor::EndOfRunActionMasterThread(int run_id){

  return 0;
  }