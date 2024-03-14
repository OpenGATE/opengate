/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateDoseSpeedTestActor.h"
#include "G4Navigator.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

#include "G4Deuteron.hh"
#include "G4Electron.hh"
#include "G4EmCalculator.hh"
#include "G4Gamma.hh"
#include "G4MaterialTable.hh"
#include "G4NistManager.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleTable.hh"
#include "G4Positron.hh"
#include "G4Proton.hh"
#include "G4Threading.hh"
#include "G4Types.hh"

// Mutex that will be used by thread to write in the edep/dose image
// TODO
G4Mutex EndOfRunMutex = G4MUTEX_INITIALIZER;

GateDoseSpeedTestActor::GateDoseSpeedTestActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  // Create the image pointer
  // (the size and allocation will be performed on the py side)
  cpp_reference_image = ImageType::New();
  // Action for this actor: during stepping
  fActions.insert("SteppingAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("EndOfRunAction");
  fActions.insert("EndSimulationAction");
  fInitialTranslation = DictGetG4ThreeVector(user_info, "translation");
  fstorageMethod = DictGetStr(user_info, "storage_method");
  fcountWriteAttempts = DictGetBool(user_info, "count_write_attempts");
}

GateDoseSpeedTestActor::~GateDoseSpeedTestActor() {
  delete deposit_vector_atomic_pointer;
}

void GateDoseSpeedTestActor::ActorInitialize() {
  fNumberOfThreads = G4Threading::GetNumberOfRunningWorkerThreads();
  if (fNumberOfThreads == 0) {
    fNumberOfThreads = 1;
  }
}

void GateDoseSpeedTestActor::PrepareStorage() {
  ImageType::RegionType region =
      cpp_reference_image->GetLargestPossibleRegion();
  fimageSize = region.GetSize();
  fnumberOfVoxels = fimageSize[0] * fimageSize[1] * fimageSize[2];

  cpp_image = ImageType::New();
  cpp_image->CopyInformation(cpp_reference_image);
  RegionType region_cpp_image;
  region_cpp_image.SetIndex(
      cpp_reference_image->GetLargestPossibleRegion().GetIndex());
  region_cpp_image.SetSize(
      cpp_reference_image->GetLargestPossibleRegion().GetSize());
  cpp_image->SetRegions(region_cpp_image);
  cpp_image->Allocate();

  if (fstorageMethod == "atomic") {
    for (int i = 0; i < fnumberOfVoxels; i++) {
      deposit_vector.emplace_back();
    }
  } else if (fstorageMethod == "standard") {
    for (int i = 0; i < fnumberOfVoxels; i++) {
      deposit_vector_standard.emplace_back(0);
    }
  } else if (fstorageMethod == "atomic_vec_pointer") {
    delete deposit_vector_atomic_pointer;
    deposit_vector_atomic_pointer =
        new std::vector<std::atomic<double>>(fnumberOfVoxels);
  }
}

void GateDoseSpeedTestActor::PrepareStorageLocal() {
  auto &l = fThreadLocalData.Get();
  l.deposit_vector_local.resize(fnumberOfVoxels);
  std::fill(l.deposit_vector_local.begin(), l.deposit_vector_local.end(), 0.0);
}

void GateDoseSpeedTestActor::BeginOfRunAction(const G4Run *) {

  if (fstorageMethod == "local") {
    PrepareStorageLocal();
  }

  // Important ! The volume may have moved, so we re-attach each run
  AttachImageToVolume<ImageType>(cpp_reference_image, fPhysicalVolumeName,
                                 fInitialTranslation);
  // compute volume of a dose voxel
  auto sp = cpp_reference_image->GetSpacing();
  fVoxelVolume = sp[0] * sp[1] * sp[2];
}

void GateDoseSpeedTestActor::SteppingAction(G4Step *step) {
  auto position = step->GetPostStepPoint()->GetPosition();
  auto touchable = step->GetPreStepPoint()->GetTouchable();
  auto localPosition =
      touchable->GetHistory()->GetTransform(0).TransformPoint(position);

  // convert G4ThreeVector to itk PointType
  ImageType::PointType point;
  point[0] = localPosition[0];
  point[1] = localPosition[1];
  point[2] = localPosition[2];

  // get pixel index
  ImageType::IndexType index;
  bool isInside =
      cpp_reference_image->TransformPhysicalPointToIndex(point, index);

  // set value
  if (isInside) {
    auto w = step->GetTrack()->GetWeight();
    auto edep = step->GetTotalEnergyDeposit() / CLHEP::MeV * w;
    int index_1d = (int)cpp_reference_image->ComputeOffset(index);
    ftotalDepositWrites++;
    if (fstorageMethod == "atomic") {
      if (fcountWriteAttempts == true) {
        ftotalReattemptsAtomicAdd += atomic_add_double_return_reattempts(
            deposit_vector[index_1d].dep, edep);
      } else {
        atomic_add_double(deposit_vector[index_1d].dep, edep);
      }
    } else if (fstorageMethod == "standard") {
      deposit_vector_standard[index_1d] += edep;
    } else if (fstorageMethod == "local") {
      auto &l = fThreadLocalData.Get();
      l.deposit_vector_local[index_1d] += edep;
    } else if (fstorageMethod == "atomic_vec_pointer") {
      if (fcountWriteAttempts == true) {
        ftotalReattemptsAtomicAdd += atomic_add_double_return_reattempts(
            (*deposit_vector_atomic_pointer)[index_1d], edep);
      } else {
        atomic_add_double((*deposit_vector_atomic_pointer)[index_1d], edep);
      }
    }
  } // else : outside the image
}

void GateDoseSpeedTestActor::EndSimulationAction() {
  if (fstorageMethod == "atomic" || fstorageMethod == "standard" ||
      fstorageMethod == "atomic_vec_pointer") {
    PrepareOutput();
  }
}

void GateDoseSpeedTestActor::EndOfRunAction(const G4Run *run) {
  if (fstorageMethod == "local") {
    WriteOutputToImageLocal();
  }
}

void GateDoseSpeedTestActor::WriteOutputToImageLocal() {
  G4AutoLock mutex(&EndOfRunMutex);

  int index_1d;
  auto &l = fThreadLocalData.Get();
  ImageIteratorType it(cpp_image, cpp_image->GetLargestPossibleRegion());
  it.GoToBegin();
  while (!it.IsAtEnd()) {
    index_1d = (int)cpp_reference_image->ComputeOffset(it.GetIndex());
    ImageAddValue<ImageType>(cpp_image, it.GetIndex(),
                             l.deposit_vector_local[index_1d]);
    ++it;
  }
}

void GateDoseSpeedTestActor::PrepareOutput() {
  int index_1d;
  ImageIteratorType it(cpp_image, cpp_image->GetLargestPossibleRegion());
  it.GoToBegin();
  while (!it.IsAtEnd()) {
    index_1d = (int)cpp_reference_image->ComputeOffset(it.GetIndex());
    if (fstorageMethod == "atomic") {
      it.Set(deposit_vector[index_1d].dep);
    } else if (fstorageMethod == "standard") {
      it.Set(deposit_vector_standard[index_1d]);
    } else if (fstorageMethod == "atomic_vec_pointer") {
      it.Set((*deposit_vector_atomic_pointer)[index_1d]);
    }
    ++it;
  }
}
