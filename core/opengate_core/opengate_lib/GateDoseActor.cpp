/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "G4Electron.hh"
#include "G4EmCalculator.hh"
#include "G4Gamma.hh"
#include "G4NistManager.hh"
#include "G4ParticleDefinition.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "G4Threading.hh"

#include "GateDoseActor.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

#include <cmath>
#include <iostream>
#include <itkAddImageFilter.h>
#include <itkImageRegionIterator.h>
#include <queue>
#include <vector>

// Mutex that will be used by thread to write in the edep/dose image
G4Mutex SetWorkerEndRunMutex = G4MUTEX_INITIALIZER;
G4Mutex SetPixelMutex = G4MUTEX_INITIALIZER;
G4Mutex ComputeUncertaintyMutex = G4MUTEX_INITIALIZER;
G4Mutex SetNbEventMutex = G4MUTEX_INITIALIZER;

GateDoseActor::GateDoseActor(py::dict &user_info)
    : GateVActor(user_info, true) {

  fUncertaintyGoal = 0.0;
  fThreshEdepPerc = 0.0;
  fOvershoot = 0.0;
  fNbEventsFirstCheck = 0;
  fNbEventsNextCheck = 0;
  fGoalUncertainty = 0.0;
  fNbOfEvent = 0;
}

void GateDoseActor::InitializeUserInfo(py::dict &user_info) {
  // IMPORTANT: call the base class method
  GateVActor::InitializeUserInfo(user_info);

  // translation
  fTranslation = DictGetG4ThreeVector(user_info, "translation");
  // Hit type (random, pre, post, etc)
  fHitType = DictGetStr(user_info, "hit_type");
}

void GateDoseActor::InitializeCpp() {
  GateVActor::InitializeCpp();

  // Create the image pointers
  // (the size and allocation will be performed on the py side)
  cpp_edep_image = Image3DType::New();

  if (fDoseFlag) {
    cpp_dose_image = Image3DType::New();
  }
  if (fEdepSquaredFlag) {
    cpp_edep_squared_image = Image3DType::New();
  }
  if (fDoseSquaredFlag) {
    cpp_dose_squared_image = Image3DType::New();
  }
  if (fCountsFlag) {
    cpp_counts_image = Image3DType::New();
  }
}

void GateDoseActor::BeginOfRunActionMasterThread(int run_id) {
  // Reset the number of events (per run)
  fNbOfEvent = 0;

  // for stop on target uncertainty. As we reset the nb of events, we reset also
  // this variable
  fNbEventsNextCheck = fNbEventsFirstCheck;

  // Important ! The volume may have moved, so we re-attach each run
  AttachImageToVolume<Image3DType>(cpp_edep_image, fPhysicalVolumeName,
                                   fTranslation);
  auto sp = cpp_edep_image->GetSpacing();
  fVoxelVolume = sp[0] * sp[1] * sp[2];

  // compute volume of a dose voxel
  Image3DType::RegionType region = cpp_edep_image->GetLargestPossibleRegion();
  size_edep = region.GetSize();

  if (fEdepSquaredFlag) {
    AttachImageToVolume<Image3DType>(cpp_edep_squared_image,
                                     fPhysicalVolumeName, fTranslation);
  }
  if (fDoseFlag) {
    AttachImageToVolume<Image3DType>(cpp_dose_image, fPhysicalVolumeName,
                                     fTranslation);
  }
  if (fDoseSquaredFlag) {
    AttachImageToVolume<Image3DType>(cpp_dose_squared_image,
                                     fPhysicalVolumeName, fTranslation);
  }
  if (fCountsFlag) {
    AttachImageToVolume<Image3DType>(cpp_counts_image, fPhysicalVolumeName,
                                     fTranslation);
  }
}

void GateDoseActor::PrepareLocalDataForRun(threadLocalT &data,
                                           const unsigned int numberOfVoxels) {
  data.squared_worker_flatimg.resize(numberOfVoxels);
  std::fill(data.squared_worker_flatimg.begin(),
            data.squared_worker_flatimg.end(), 0.0);
  data.lastid_worker_flatimg.resize(numberOfVoxels);
  std::fill(data.lastid_worker_flatimg.begin(),
            data.lastid_worker_flatimg.end(), 0);
}

void GateDoseActor::BeginOfRunAction(const G4Run *run) {
  const auto N_voxels = size_edep[0] * size_edep[1] * size_edep[2];
  if (fEdepSquaredFlag) {
    PrepareLocalDataForRun(fThreadLocalDataEdep.Get(), N_voxels);
  }
  if (fDoseSquaredFlag) {
    PrepareLocalDataForRun(fThreadLocalDataDose.Get(), N_voxels);
  }
}

void GateDoseActor::BeginOfEventAction(const G4Event *event) {
  G4AutoLock mutex(&SetNbEventMutex);
  fNbOfEvent++;
}

void GateDoseActor::GetVoxelPosition(G4Step *step, G4ThreeVector &position,
                                     bool &isInside,
                                     Image3DType::IndexType &index) const {
  auto preGlobal = step->GetPreStepPoint()->GetPosition();
  auto postGlobal = step->GetPostStepPoint()->GetPosition();
  auto touchable = step->GetPreStepPoint()->GetTouchable();

  // consider random position between pre and post
  if (fHitType == "pre") {
    position = preGlobal;
  }
  if (fHitType == "post") {
    position = postGlobal;
  }
  if (fHitType == "random") {
    auto x = G4UniformRand();
    auto direction = postGlobal - preGlobal;
    position = preGlobal + x * direction;
  }
  if (fHitType == "middle") {
    auto direction = postGlobal - preGlobal;
    position = preGlobal + 0.5 * direction;
  }

  auto localPosition =
      touchable->GetHistory()->GetTransform(0).TransformPoint(position);

  // convert G4ThreeVector to itk PointType
  Image3DType::PointType point;
  point[0] = localPosition[0];
  point[1] = localPosition[1];
  point[2] = localPosition[2];

  isInside = cpp_edep_image->TransformPhysicalPointToIndex(point, index);
}

void GateDoseActor::SteppingAction(G4Step *step) {
  const auto event_id =
      G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
  auto preGlobal = step->GetPreStepPoint()->GetPosition();
  auto postGlobal = step->GetPostStepPoint()->GetPosition();

  // FIXME If the volume has multiple copy, touchable->GetCopyNumber(0) ?

  // Get the voxel index
  G4ThreeVector position;
  bool isInside;
  Image3DType::IndexType index;
  GetVoxelPosition(step, position, isInside, index);

  if (isInside) {

    // get edep in MeV (take weight into account)
    const auto w = step->GetTrack()->GetWeight();
    auto edep = step->GetTotalEnergyDeposit() / CLHEP::MeV * w;
    double dose;

    if (fToWaterFlag) {
      auto *current_material = step->GetPreStepPoint()->GetMaterial();
      double dedx_cut = DBL_MAX;
      double dedx_currstep = 0., dedx_water = 0.;
      const G4ParticleDefinition *p = step->GetTrack()->GetParticleDefinition();
      static G4Material *water =
          G4NistManager::Instance()->FindOrBuildMaterial("G4_WATER");
      auto energy1 = step->GetPreStepPoint()->GetKineticEnergy();
      auto energy2 = step->GetPostStepPoint()->GetKineticEnergy();
      auto energy = (energy1 + energy2) / 2;
      if (p == G4Gamma::Gamma())
        p = G4Electron::Electron();
      auto &emc = fThreadLocalDataEdep.Get().emcalc;
      dedx_currstep =
          emc.ComputeTotalDEDX(energy, p, current_material, dedx_cut);
      dedx_water = emc.ComputeTotalDEDX(energy, p, water, dedx_cut);
      if (dedx_currstep == 0 || dedx_water == 0) {
        edep = 0.;
      } else {
        edep *= (dedx_water / dedx_currstep);
      }
    }

    if (fDoseFlag || fDoseSquaredFlag) {
      double density;
      if (fToWaterFlag) {
        const auto *water =
            G4NistManager::Instance()->FindOrBuildMaterial("G4_WATER");
        density = water->GetDensity();
      } else {
        const auto *current_material = step->GetPreStepPoint()->GetMaterial();
        density = current_material->GetDensity();
      }
      dose = edep / density;
    }

    // all ImageAddValue calls in a mutex-scope
    {
      G4AutoLock mutex(&SetPixelMutex);
      ImageAddValue<Image3DType>(cpp_edep_image, index, edep);
      if (fDoseFlag) {
        ImageAddValue<Image3DType>(cpp_dose_image, index, dose);
      }
      if (fCountsFlag) {
        ImageAddValue<Image3DType>(cpp_counts_image, index, 1);
      }
    } // mutex scope

    // ScoreSquaredValue() is thread-safe because it contains a mutex
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
  } // if(isInside) clause
}

void GateDoseActor::EndOfEventAction(const G4Event *event) {
  // if the user didn't set an uncertainty goal, do nothing
  if (fUncertaintyGoal == 0) {
    return;
  }

  // check if we reached the Nb of events for the next evaluation
  if (fNbOfEvent >= fNbEventsNextCheck) {
    // flush thread local data into the global image
    // reset local data to zero is done in FlushSquaredValue
    if (fEdepSquaredFlag) {
      FlushSquaredValues(fThreadLocalDataEdep.Get(), cpp_edep_squared_image);
    }
    if (fDoseSquaredFlag) {
      FlushSquaredValues(fThreadLocalDataDose.Get(), cpp_dose_squared_image);
    }

    // Get thread idx. Ideally, only one thread should do the uncertainty
    // calculation don't ask for thread idx if no MT
    if (!G4Threading::IsMultithreadedApplication() ||
        G4Threading::G4GetThreadId() == 0) {
      // check stop criteria
      double UncCurrent = ComputeMeanUncertainty();
      if (UncCurrent <= fUncertaintyGoal) {
        GateSourceManager::SetRunTerminationFlag(true);
      } else {
        // estimate nb of events at which the next check should occur
        fNbEventsNextCheck = static_cast<int>((UncCurrent / fUncertaintyGoal) *
                                              (UncCurrent / fUncertaintyGoal) *
                                              fNbOfEvent * fOvershoot);
      }
    }
  }
}

double GateDoseActor::ComputeMeanUncertainty() {
  G4AutoLock mutex(&ComputeUncertaintyMutex);
  itk::ImageRegionIterator<Image3DType> edep_iterator3D(
      cpp_edep_image, cpp_edep_image->GetLargestPossibleRegion());
  double mean_unc = 0.0;
  int n_voxel_unc = 0;
  double n = 2.0;
  n = fNbOfEvent;

  if (n < 2.0) {
    n = 2.0;
  }
  double max_edep = GetMaxValueOfImage(cpp_edep_image);

  for (edep_iterator3D.GoToBegin(); !edep_iterator3D.IsAtEnd();
       ++edep_iterator3D) {
    Image3DType::IndexType index_f = edep_iterator3D.GetIndex();
    double val = cpp_edep_image->GetPixel(index_f);

    if (val > max_edep * fThreshEdepPerc) {
      val /= n;
      n_voxel_unc++;
      const double val_squared_mean =
          cpp_edep_squared_image->GetPixel(index_f) / n;

      double unc_i = (1.0 / (n - 1.0)) * (val_squared_mean - pow(val, 2));
      if (unc_i < 0) {
        std::cout << "unc_i: " << unc_i << std::endl;
        std::cout << "edep: " << val << std::endl;
        std::cout << "edep_squared_mean: " << val_squared_mean << std::endl;
      }

      unc_i = sqrt(unc_i) / (val);

      if (unc_i > 1) {
        std::cout << "unc_i: " << unc_i << std::endl;
        std::cout << "edep: " << val << std::endl;
        std::cout << "edep_squared_mean: " << val_squared_mean << std::endl;
      }
      mean_unc += unc_i;
    }
  };

  if (n_voxel_unc > 0 && mean_unc > 0) {
    mean_unc = mean_unc / n_voxel_unc;
  } else {
    mean_unc = 1.;
  }
  return mean_unc;
}

int GateDoseActor::sub2ind(Image3DType::IndexType index3D) {
  return index3D[0] + size_edep[0] * (index3D[1] + size_edep[1] * index3D[2]);
}

void GateDoseActor::ind2sub(int index_flat, Image3DType::IndexType &index3D) {
  int z = index_flat / (size_edep[0] * size_edep[1]);
  index_flat %= size_edep[0] * size_edep[1];
  int y = index_flat / size_edep[0];
  int x = index_flat % size_edep[0];
  // Image3DType::IndexType index;
  index3D[0] = x;
  index3D[1] = y;
  index3D[2] = z;
}

void GateDoseActor::EndOfRunAction(const G4Run *run) {
  // FlushSquaredValue() is thread-safe because it contains a mutex
  if (fEdepSquaredFlag) {
    GateDoseActor::FlushSquaredValues(fThreadLocalDataEdep.Get(),
                                      cpp_edep_squared_image);
  }
  if (fDoseSquaredFlag) {
    GateDoseActor::FlushSquaredValues(fThreadLocalDataDose.Get(),
                                      cpp_dose_squared_image);
  }
}

void GateDoseActor::ScoreSquaredValue(threadLocalT &data,
                                      const Image3DType::Pointer &cpp_image,
                                      const double value, const int event_id,
                                      const Image3DType::IndexType &index) {
  const int index_flat = sub2ind(index);
  const auto previous_id = data.lastid_worker_flatimg[index_flat];
  data.lastid_worker_flatimg[index_flat] = event_id;
  if (event_id == previous_id) {
    // Same event: sum the deposited value associated with this event ID
    // and square once a new event ID is found (case below)
    data.squared_worker_flatimg[index_flat] += value;
  } else {
    // Different event: square deposited quantity from the last event ID
    // and start accumulating deposited quantity for this new event ID
    auto v = data.squared_worker_flatimg[index_flat];
    {
      G4AutoLock mutex(&SetPixelMutex);
      ImageAddValue<Image3DType>(cpp_image, index, v * v); // implicit flush
    }
    // new temp value
    data.squared_worker_flatimg[index_flat] = value;
  }
}

void GateDoseActor::FlushSquaredValues(threadLocalT &data,
                                       const Image3DType::Pointer &cpp_image) {
  G4AutoLock mutex(&SetPixelMutex);
  itk::ImageRegionIterator<Image3DType> iterator3D(
      cpp_image, cpp_image->GetLargestPossibleRegion());
  for (iterator3D.GoToBegin(); !iterator3D.IsAtEnd(); ++iterator3D) {
    Image3DType::IndexType index_f = iterator3D.GetIndex();
    Image3DType::PixelType pixelValue3D =
        data.squared_worker_flatimg[sub2ind(index_f)];
    ImageAddValue<Image3DType>(cpp_image, index_f, pixelValue3D * pixelValue3D);
  }
  // reset thread local data to zero
  const auto N_voxels = size_edep[0] * size_edep[1] * size_edep[2];
  PrepareLocalDataForRun(data, N_voxels);
}

int GateDoseActor::EndOfRunActionMasterThread(int run_id) { return 0; }

double GateDoseActor::GetMaxValueOfImage(Image3DType::Pointer imageP) {
  itk::ImageRegionIterator<Image3DType> iterator3D(
      imageP, imageP->GetLargestPossibleRegion());
  Image3DType::PixelType max = 0;
  Image3DType::IndexType index_max;
  // keep track of the 10 highest values of the image
  std::priority_queue<double, std::vector<double>, std::greater<double>> pq;
  for (iterator3D.GoToBegin(); !iterator3D.IsAtEnd(); ++iterator3D) {
    Image3DType::IndexType index_f = iterator3D.GetIndex();
    Image3DType::PixelType val = imageP->GetPixel(index_f);
    if (val > max) {
      max = val;
      index_max = index_f;
      pq.push(max);
      if (pq.size() > 10) {
        pq.pop();
      }
    }
  }
  return max;
}
