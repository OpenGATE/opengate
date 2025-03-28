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
#include "GateVoxelizedPromptGammaTLEActor.h"
#include "G4HadronInelasticProcess.hh"


#include <iostream>
#include <itkAddImageFilter.h>
#include <itkImageRegionIterator.h>
#include <itkImageFileWriter.h>
#include <itkCastImageFilter.h>
#include <vector>



GateVoxelizedPromptGammaTLEActor::GateVoxelizedPromptGammaTLEActor(
    py::dict &user_info)
    : GateVActor(user_info, true) {
  fMultiThreadReady = true;
}

void GateVoxelizedPromptGammaTLEActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  fTranslation = DictGetG4ThreeVector(user_info,"translation");
  fsize = DictGetG4ThreeVector(user_info,"size");
  fspacing = DictGetG4ThreeVector(user_info,"spacing");
  Nbbinstime = py::int_(user_info["timebins"]);
  Nbbinsenergy = py::int_(user_info["energybins"]);
  foutputname = std::string(py::str(user_info["output_name"]));
}

void GateVoxelizedPromptGammaTLEActor::InitializeCpp() {
  GateVActor::InitializeCpp(); 
  
  //Initialisation of the cpp images
  //spatial volume
  Volume = Image3DType::New();
  Image3DType::RegionType region3;
  Image3DType::SpacingType spacing3;
  Image3DType::SizeType size3;
  Image3DType::PointType origin;

  size3[0] = fsize[0]; 
  size3[1] = fsize[1]; 
  size3[2] = fsize[2]; 

  region3.SetSize(size3);
  
  spacing3[0] = fspacing[0];
  spacing3[1] = fspacing[1]; 
  spacing3[2] = fspacing[2];
  

  origin[0] = fTranslation[0];
  origin[1] = fTranslation[1]; 
  origin[2] = fTranslation[2]; 
  
  Volume->SetRegions(region3);
  Volume->SetSpacing(spacing3);
  Volume->SetOrigin(origin);
  Volume->Allocate();
  Volume->FillBuffer(0);

  //output image
  output_image = Image2DType::New();

  Image2DType::RegionType region;
  Image2DType::SizeType size;
  Image2DType::SpacingType spacing;

  size[0] = Nbbinsenergy; 
  size[1] = Nbbinstime;  

  region.SetSize(size);

  spacing[0] = 1.0; 
  spacing[1] = 1.0;

  output_image->SetRegions(region);
  output_image->SetSpacing(spacing);
  output_image->Allocate();
  output_image->FillBuffer(0);

  //Initialisation of the incident particle scorer
  incidentParticles = 0;
  creationtime = 0;
}


void GateVoxelizedPromptGammaTLEActor::BeginOfRunActionMasterThread(int run_id) {
  AttachImageToVolume<Image3DType>(Volume, fPhysicalVolumeName, fTranslation);
}

void GateVoxelizedPromptGammaTLEActor::BeginOfRunAction(const G4Run *run) {}

void GateVoxelizedPromptGammaTLEActor::BeginOfEventAction(
    const G4Event *event) {
    incidentParticles++;
    }


void GateVoxelizedPromptGammaTLEActor::SteppingAction(G4Step *step) {
  //If the particule treated is not a neutron, no stepping action
  if (step->GetTrack()->GetParticleDefinition()->GetParticleName()!="neutron"){
    return;
  }
  //Sampling the creation time of the particule ~ time a the first pre-step of the track
  if ((step->GetTrack()->GetCurrentStepNumber()==1) && (step->GetTrack()->GetTrackID() != 1)){
    creationtime = step->GetPreStepPoint()->GetGlobalTime(); 
  } 

  //sampling the secondaries
  auto secondaries = step->GetSecondary();

  //loop on the list of secondaries 
  for (size_t i = 0; i < secondaries->size(); i++) {
    auto secondary = secondaries->at(i);
    auto secondary_def = secondary->GetParticleDefinition();

    //verifying if it's a gamma and that it's created by neutron inelastic interaction
    if ((secondary_def != G4Gamma::Gamma()) || (secondary->GetCreatorProcess()->GetProcessName() != "neutronInelastic")) {
      continue;
    }

     // Get the position of the interaction
    auto position = step->GetPostStepPoint()->GetPosition();
    auto touchable = step->GetPreStepPoint()->GetTouchable();
    auto localPosition = touchable->GetHistory()->GetTransform(0).TransformPoint(position);

      // convert G4ThreeVector to itk PointType
    Image3DType::PointType point;
    point[0] = localPosition[0];
    point[1] = localPosition[1];
    point[2] = localPosition[2];

    //verify if we are inside the volume of interest
    Image3DType::IndexType index;
    G4bool isInside = Volume->TransformPhysicalPointToIndex(point, index);
    if (!isInside) {
      return;
    } 

    Image2DType::IndexType ind;

    //Sampling the energy of the gamma
    auto energyPG = secondary->GetKineticEnergy(); 

    //defining the range and the width
    G4double energy_range_EP = 10.0 * CLHEP::MeV ; 
    G4double widthenergy =(energy_range_EP/Nbbinsenergy);

    //negative case
    if(energyPG < 0 ) energyPG = 0;

    //rough method to attribute an index to the energy
    ind[0] = static_cast<int>(energyPG / widthenergy);
    if (ind[0] >= Nbbinsenergy) {
        ind[0] = Nbbinsenergy - 1; 
      }

    //Sampling the time of the gamma emission
    G4double currenttime = step->GetPostStepPoint()->GetGlobalTime(); //ns
    G4double time = (currenttime - creationtime);//ns

    std::cout << "emission time: " << currenttime << std::endl;
    std::cout << "Creation time : " << creationtime << std::endl; 
    std::cout << "Time of flight : " << time << std::endl;

    //defining the range and the width
    G4double timerange = 15; //ns
    G4double timewidth = timerange / Nbbinstime;   

    //negative case
    if (time < 0) {
      std::cerr << "Warning: Negative time detected." << std::endl;
      time = 0;
      continue;
    }

    //rough method to attribute an index to the time
    ind[1] = static_cast<int>(time / timewidth);
    if (ind[1] >= Nbbinstime) {
      ind[1] = Nbbinstime - 1;  
    }

    //adding the value to the 2D histogram (ITKimage)
    std::cout << "Voxel index: " << ind[0] << ", " << ind[1] << std::endl;
    ImageAddValue<Image2DType>(output_image, ind, 1);
  }
}


void GateVoxelizedPromptGammaTLEActor::EndOfRunAction(const G4Run *run) {
  //Normalisation
  itk::ImageRegionIterator<Image2DType> it(output_image,output_image->GetLargestPossibleRegion());
  for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
    it.Set(it.Get() / incidentParticles);
  }
}


std::string GateVoxelizedPromptGammaTLEActor::GetOutputImage() {

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


int GateVoxelizedPromptGammaTLEActor::EndOfRunActionMasterThread(int run_id){
  return 0;
  }



