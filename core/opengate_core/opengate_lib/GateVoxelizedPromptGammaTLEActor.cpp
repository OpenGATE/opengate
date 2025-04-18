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
#include <itkImageFileWriter.h>
#include <itkImageRegionIterator.h>
#include <vector>

GateVoxelizedPromptGammaTLEActor::GateVoxelizedPromptGammaTLEActor(
    py::dict &user_info)
    : GateVActor(user_info, true) {
  fMultiThreadReady = true;
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
  }

  if (!step->GetTrack() || !step->GetSecondary()) {
    return; // Éviter les accès à des pointeurs nuls
  }

  // sampling the secondaries
  auto secondaries = step->GetSecondary();

  // loop on the list of secondaries
  for (size_t i = 0; i < secondaries->size(); i++) {
    auto secondary = secondaries->at(i);
    auto secondary_def = secondary->GetParticleDefinition();

    // verifying if it's a gamma and that it's created by neutron inelastic
    // interaction
    if ((secondary_def != G4Gamma::Gamma()) ||
        (secondary->GetCreatorProcess()->GetProcessName() !=
         "neutronInelastic")) {
      continue;
    }

    // Get the position of the interaction
    auto position = step->GetPostStepPoint()->GetPosition();
    auto touchable = step->GetPreStepPoint()->GetTouchable();
    auto localPosition =
        touchable->GetHistory()->GetTransform(0).TransformPoint(position);

    // convert G4ThreeVector to itk PointType
    Image3DType::PointType point;
    point[0] = localPosition[0];
    point[1] = localPosition[1];
    point[2] = localPosition[2];

    // verify if we are inside the volume of interest
    Image3DType::IndexType index;
    G4bool isInside = fVolume->TransformPhysicalPointToIndex(point, index);

    if (!isInside) {
      continue;
    }
    Image2DType::IndexType ind;

    // Sampling the energy of the gamma
    auto energyPG = secondary->GetKineticEnergy();

    // defining the range and the width
    G4double energy_range = 10.0 * CLHEP::MeV;
    G4double widthenergy = (energy_range / Nbbinsenergy);

    // Calculate the bin index directly
    int bin0 = static_cast<int>(energyPG / widthenergy);
    if (bin0 >= Nbbinsenergy) {
      bin0 = Nbbinsenergy - 1;
    }
    ind[0] = bin0;

    // Sampling the time of the gamma emission
    G4double currenttime = step->GetPostStepPoint()->GetGlobalTime(); // ns
    G4double time = (currenttime - creationtime);                     // ns

    std::cout << "emission time: " << currenttime << std::endl;
    std::cout << "Creation time : " << creationtime << std::endl;
    std::cout << "Time of flight : " << time << std::endl;

    // negative case
    if (time < 0) {
      std::cerr << "Warning: Negative time detected." << std::endl;
      continue;
    }

    // defining the range and the width
    G4double timerange = 2; // ns
    G4double timewidth = timerange / Nbbinstime;

    // Calculate the bin index directly
    int bin1 = static_cast<int>(time / timewidth);
    if (bin1 >= Nbbinstime) {
      bin1 = Nbbinstime - 1;
    }
    ind[1] = bin1;

    norm = norm + 1;
    // adding the value to the 2D histogram (ITKimage)
    std::cout << "Voxel index: " << ind[0] << ", " << ind[1] << std::endl;
    ImageAddValue<Image2DType>(output_image, ind, 1);
  }
}

void GateVoxelizedPromptGammaTLEActor::EndOfRunAction(const G4Run *run) {
  // Normalisation
  itk::ImageRegionIterator<Image2DType> it(
      output_image, output_image->GetLargestPossibleRegion());
  for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
    it.Set(it.Get() / incidentParticles);
  }
  std::cout << "incident proton : " << incidentParticles << std::endl;
  std::cout << "inelastic collision of neutron" << norm << std::endl;
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

int GateVoxelizedPromptGammaTLEActor::EndOfRunActionMasterThread(int run_id) {
  return 0;
}
