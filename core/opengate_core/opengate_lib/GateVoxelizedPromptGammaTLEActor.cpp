/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

<<<<<<< HEAD
#include "G4EmCalculator.hh"
#include "G4Gamma.hh"
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
=======
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
#include <itkImageFileWriter.h>
#include <itkImageRegionIterator.h>
#include <vector>

GateVoxelizedPromptGammaTLEActor::GateVoxelizedPromptGammaTLEActor(
    py::dict &user_info)
    : GateVActor(user_info, true) {
  fMultiThreadReady = false;
}

void GateVoxelizedPromptGammaTLEActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  fTranslation = DictGetG4ThreeVector(user_info, "translation");
  fsize = DictGetG4ThreeVector(user_info, "size");
  fspacing = DictGetG4ThreeVector(user_info, "spacing");
  Nbbinstime = py::int_(user_info["timebins"]);
  Nbbinsenergy = py::int_(user_info["energybins"]);
  foutputname = std::string(py::str(user_info["output_name"]));
}

void GateVoxelizedPromptGammaTLEActor::InitializeCpp() {
  GateVActor::InitializeCpp();

  // Initialisation of the cpp images
  // spatial volume
  fVolume = Image3DType::New();

  // output image
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

  // Initialisation of the incident particle scorer
  incidentParticles = 0;
  norm = 0;
}

void GateVoxelizedPromptGammaTLEActor::BeginOfRunActionMasterThread(
    int run_id) {
  auto volume =
      G4PhysicalVolumeStore::GetInstance()->GetVolume(fPhysicalVolumeName);
  if (volume) {
    auto solid = volume->GetLogicalVolume()->GetSolid();
    if (auto box = dynamic_cast<G4Box *>(solid)) {
      std::cout << "Box Dimensions: " << box->GetXHalfLength() * 2 << ", "
                << box->GetYHalfLength() * 2 << ", "
                << box->GetZHalfLength() * 2 << std::endl;

      Image3DType::RegionType region3;
      Image3DType::SizeType size3;
      Image3DType::SpacingType spacing3;

      size3[0] = fsize[0];
      size3[1] = fsize[1];
      size3[2] = fsize[2];

      region3.SetSize(size3);

      spacing3[0] = fspacing[0];
      spacing3[1] = fspacing[1];
      spacing3[2] = fspacing[2];

      fVolume->SetRegions(region3);
      fVolume->SetSpacing(spacing3);
      fVolume->Allocate();
      fVolume->FillBuffer(0);
      // Initialize fVolume for a box (if needed)
    } else if (auto tubs = dynamic_cast<G4Tubs *>(solid)) {
      std::cout << "Cylinder Dimensions: "
                << "Inner Radius: " << tubs->GetInnerRadius() << ", "
                << "Outer Radius: " << tubs->GetOuterRadius() << ", "
                << "Height: " << tubs->GetZHalfLength() * 2 << std::endl;

      // Initialize fVolume for a cylinder
      Image3DType::RegionType region3;
      Image3DType::SizeType size3;
      Image3DType::SpacingType spacing3;

      // Calculate the size and spacing based on the cylinder dimensions
      double height = tubs->GetZHalfLength() * 2;  // Full height
      double outerRadius = tubs->GetOuterRadius(); // Outer radius

      // Example: Define the resolution (adjust as needed)
      double resolution = 1.0; // 1 mm per voxel

      size3[0] = static_cast<unsigned int>(2 * outerRadius /
                                           resolution); // Diameter in X
      size3[1] = static_cast<unsigned int>(2 * outerRadius /
                                           resolution); // Diameter in Y
      size3[2] = static_cast<unsigned int>(height / resolution); // Height in Z

      spacing3[0] = resolution; // Spacing in X
      spacing3[1] = resolution; // Spacing in Y
      spacing3[2] = resolution; // Spacing in Z

      region3.SetSize(size3);

      fVolume->SetRegions(region3);
      fVolume->SetSpacing(spacing3);
      fVolume->Allocate();
      fVolume->FillBuffer(0);

      std::cout << "Initialized ITK image for cylinder:" << std::endl;
      std::cout << "Size: " << size3[0] << ", " << size3[1] << ", " << size3[2]
                << std::endl;
      std::cout << "Spacing: " << spacing3[0] << ", " << spacing3[1] << ", "
                << spacing3[2] << std::endl;
    } else {
      std::cerr << "Unsupported solid type: " << solid->GetName() << std::endl;
    }
  } else {
    std::cerr << "Volume not found: " << fPhysicalVolumeName << std::endl;
  }
  AttachImageToVolume<Image3DType>(fVolume, fPhysicalVolumeName, fTranslation);
  std::cout << "AFTER" << std::endl;
  std::cout << "size" << fVolume->GetLargestPossibleRegion().GetSize()
            << std::endl;
  std::cout << "Direction" << fVolume->GetDirection() << std::endl;
  std::cout << "index" << fVolume->GetLargestPossibleRegion().GetIndex()
            << std::endl;
  std::cout << "spacing" << fVolume->GetSpacing() << std::endl;
  std::cout << "origin" << fVolume->GetOrigin() << std::endl;
}

void GateVoxelizedPromptGammaTLEActor::BeginOfRunAction(const G4Run *run) {}

void GateVoxelizedPromptGammaTLEActor::BeginOfEventAction(
    const G4Event *event) {
  incidentParticles++;
  creationtime = event->GetPrimaryVertex()->GetT0();
}

void GateVoxelizedPromptGammaTLEActor::SteppingAction(G4Step *step) {
  // If the particule treated is not a neutron, no stepping action
  if (step->GetTrack()->GetParticleDefinition()->GetParticleName() !=
      "neutron") {
    return;
>>>>>>> 9b6b31a2805308283a15bc5a0006868397adf09a
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
  std::cout << bins << range << std::endl;
  std::cout << "particle of interest is proton : " << prot << std::endl;
}

void GateVoxelizedPromptGammaTLEActor::InitializeCpp() {
  GateVActor::InitializeCpp();
  // Create the image pointers
  // (the size and allocation will be performed on the py side)
  cpp_image = ImageType::New();
  norm = 0;
  incidentParticles = 0;
}

void GateVoxelizedPromptGammaTLEActor::BeginOfRunActionMasterThread(
    int run_id) {}

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
  if (!isInside) {
    return; // Skip if not inside the volume
  }
  // Get the particle type
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

  /*
  if ((step->GetTrack()->GetParentID() != 0) &&
  (step->GetTrack()->GetCurrentStepNumber() == 1)) { T0 =
  step->GetTrack()->GetGlobalTime();
  } */

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
    if (secondary->GetCreatorProcess()->GetProcessName() !=
            "neutronInelastic" &&
        !prot) {
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
    std::cout << "Voxel index: " << ind[0] << ", " << ind[1] << ", " << ind[2]
              << ", " << ind[3] << " for the time : " << time << std::endl;
    if (prot) {
      std::cout << "Proton inelastic collision of interest" << std::endl;
    } else {
      std::cout << "Neutron inelastic collision of interest" << std::endl;
    }
    cpp_image->SetPixel(ind, cpp_image->GetPixel(ind) + 1);
    norm = norm + 1;
  }
}

void GateVoxelizedPromptGammaTLEActor::EndOfRunAction(const G4Run *run) {
  itk::ImageRegionIterator<ImageType> it(cpp_image,
                                         cpp_image->GetLargestPossibleRegion());
  for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
    it.Set(it.Get() / norm);
  }
  std::cout << "incident proton : " << incidentParticles << std::endl;
  std::cout << "inelastic collision of interest " << norm << " for " << prot
            << std::endl;
}

int GateVoxelizedPromptGammaTLEActor::EndOfRunActionMasterThread(int run_id) {
  return 0;
}
