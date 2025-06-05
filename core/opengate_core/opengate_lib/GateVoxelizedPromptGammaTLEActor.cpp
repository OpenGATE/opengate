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

#include "CLHEP/Random/Randomize.h"
#include <iostream>
#include <itkAddImageFilter.h>
#include <itkCastImageFilter.h>
#include <itkImageRegionIterator.h>
#include <vector>

GateVoxelizedPromptGammaTLEActor::GateVoxelizedPromptGammaTLEActor(
    py::dict &user_info)
    : GateVActor(user_info, true) {
  fMultiThreadReady =
      true; // But used as a single thread python side : nb pf runs = 1
}

GateVoxelizedPromptGammaTLEActor::~GateVoxelizedPromptGammaTLEActor() {
  // not needed
}

void GateVoxelizedPromptGammaTLEActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);

  // retrieve the python param here
  bins = py::int_(user_info["bins"]);
  range = py::float_(user_info["range"]);

  // Boolean to know the quantity and projectile of interest
  prot = py::bool_(user_info["proton"]);   // True => proton wanted
  energy = py::bool_(user_info["energy"]); // True => Energy wanted

  fTranslation = DictGetG4ThreeVector(user_info, "translation");
  fHitType = DictGetStr(user_info, "hit_type");
  fsize = DictGetG4ThreeVector(user_info, "size");
  fspacing = DictGetG4ThreeVector(user_info, "spacing");
}

void GateVoxelizedPromptGammaTLEActor::InitializeCpp() {
  GateVActor::InitializeCpp();

  // Create the image pointers
  // (the size and allocation will be performed on the py side)
  if (!prot) {
    if (!energy) {
      cpp_tof_neutron_image = ImageType::New();
      cpp_tof_proton_image = nullptr;
      cpp_E_neutron_image = nullptr;
      cpp_E_proton_image = nullptr;
    } else {
      cpp_tof_neutron_image = nullptr;
      cpp_tof_proton_image = nullptr;
      cpp_E_neutron_image = ImageType::New();
      cpp_E_proton_image = nullptr;
    }
  } else {
    if (!energy) {
      cpp_tof_neutron_image = nullptr;
      cpp_tof_proton_image = ImageType::New();
      cpp_E_neutron_image = nullptr;
      cpp_E_proton_image = nullptr;
    } else {
      cpp_tof_neutron_image = nullptr;
      cpp_tof_proton_image = nullptr;
      cpp_E_neutron_image = nullptr;
      cpp_E_proton_image = ImageType::New();
    }
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
  width = range / bins; // width calculated in the initiation to facilitate the
                        // binning later
}

void GateVoxelizedPromptGammaTLEActor::BeginOfRunActionMasterThread(
    int run_id) {

  // Attach the 3D volume used to
  AttachImageToVolume<Image3DType>(volume, fPhysicalVolumeName, fTranslation);

  // Fill the 4D volume of interest with 0 to ensure that it is well initiated
  if (prot) {
    if (energy) {
      cpp_E_proton_image->FillBuffer(0);
    } else {
      cpp_tof_proton_image->FillBuffer(0);
    }
  } else {
    if (energy) {
      cpp_E_neutron_image->FillBuffer(0);
    } else {
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

  // Get the voxel index
  G4ThreeVector position;
  G4bool isInside;
  Image3DType::IndexType index;
  GetStepVoxelPosition<Image3DType>(step, fHitType, volume, position, isInside,
                                    index);

  if (!isInside) { // verification
    return;        // Skip if not inside the volume
  }

  // Get the weight of the track (particle history) for potential russian
  // roulette or splitting
  G4double w = step->GetTrack()->GetWeight();

  // Get the spatial index from the index obtained with the 3D volume and th
  // emethod GetStepVoxelPosition()
  ImageType::IndexType ind;
  ind[0] = index[0];
  ind[1] = index[1];
  ind[2] = index[2];

  // Initiate the bin (fourth index) at 0
  int bin = 0;

  if (!energy) { // If the quantity of interest is the time of flight

    // Get the time of flight
    G4double randomtime = G4UniformRand();
    G4double pretime = step->GetPreStepPoint()->GetGlobalTime() - T0;
    G4double posttime = step->GetPostStepPoint()->GetGlobalTime() - T0;
    G4double time = (pretime + randomtime * (posttime - pretime));

    // Get the voxel index (fourth dim) corresponding to the time of flight
    G4int bin = static_cast<int>(time / width); // Always the left bin
    if (bin == bins) {
      bin = bins - 1;
    }
    ind[3] = bin;
    std::cout << "tof = " << time << std::endl;
    std::cout << "bin = " << bin << std::endl;
    // Store the value in the volume for neutrons OR protons -> LEFT BINNING
    if (prot) {
      ImageAddValue<ImageType>(cpp_tof_proton_image, ind, w);
    } else {
      ImageAddValue<ImageType>(cpp_tof_neutron_image, ind, w);
    }

  } else { // when the quantity of interest is the energy

    // Get the energy of the projectile
    G4double randomenergy = G4UniformRand();
    const G4double &postE = step->GetPostStepPoint()->GetKineticEnergy();
    const G4double &preE = step->GetPreStepPoint()->GetKineticEnergy();
    G4double projectileEnergy = postE + randomenergy * (preE - postE);

    // thershold with a minimum energy of 40 keV
    if (projectileEnergy < 0.04 * CLHEP::MeV) {
      return;
    }

    // Get the voxel index (fourth dim) corresponding to the energy of the
    // projectile
    bin = static_cast<int>(projectileEnergy / width); // Always the left bin
    if (bin == bins) {
      bin = bins - 1;
    }
    ind[3] = bin;

    std::cout << "energy = " << projectileEnergy << std::endl;
    std::cout << "bin = " << bin << std::endl;

    // Get the step lenght
    const G4double &l = step->GetStepLength();

    // Store the value in the volume for neutrons OR protons -> LEFT BINNING
    if (prot) {
      ImageAddValue<ImageType>(cpp_E_proton_image, ind, w * l);
    } else {
      ImageAddValue<ImageType>(cpp_E_neutron_image, ind, w * l);
    }
  }
}

void GateVoxelizedPromptGammaTLEActor::EndOfRunAction(const G4Run *run) {
  std::cout << "incident proton : " << incidentParticles << std::endl;

  // scaling all the 4D voxels with th enumber of incident protons (= number of
  // event)
  if (prot) {
    if (!energy) {
      itk::ImageRegionIterator<ImageType> it(
          cpp_tof_proton_image,
          cpp_tof_proton_image->GetLargestPossibleRegion());
      for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
        it.Set(it.Get() / incidentParticles);
      }
    } else {
      itk::ImageRegionIterator<ImageType> it(
          cpp_E_proton_image, cpp_E_proton_image->GetLargestPossibleRegion());
      for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
        it.Set(it.Get() / incidentParticles);
      }
    }
  } else {
    if (!energy) {
      itk::ImageRegionIterator<ImageType> it(
          cpp_tof_neutron_image,
          cpp_tof_neutron_image->GetLargestPossibleRegion());
      for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
        it.Set(it.Get() / incidentParticles);
      }
    } else {
      itk::ImageRegionIterator<ImageType> it(
          cpp_E_neutron_image, cpp_E_neutron_image->GetLargestPossibleRegion());
      for (it.GoToBegin(); !it.IsAtEnd(); ++it) {
        it.Set(it.Get() / incidentParticles);
      }
    }
  }
}

int GateVoxelizedPromptGammaTLEActor::EndOfRunActionMasterThread(int run_id) {
  return 0;
}
