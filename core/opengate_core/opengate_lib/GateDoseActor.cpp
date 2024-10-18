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
    : GateVActor(user_info, true) {}

void GateDoseActor::InitializeUserInput(py::dict &user_info) {
  // IMPORTANT: call the base class method
  GateVActor::InitializeUserInput(user_info);
  //  //  Option: compute uncertainty
  //  fUncertaintyFlag = DictGetBool(user_info, "uncertainty");
  // Option: compute square
  //  fSquareFlag = DictGetBool(user_info, "square");
  //  // Option: compute dose in Gray
  //  fDoseFlag = DictGetBool(user_info, "dose");
  // Option: compute dose to water
  fScoreIn = DictGetStr(user_info, "score_in");
  // DDD(fScoreIn);
  //  // Option: calculate only edep/edepToWater, and divide by mass image on
  //  python
  //  // side
  //  fOnFlyCalcFlag = DictGetBool(user_info, "dose_calc_on_the_fly");

  //  // Option to stop the simulation when a stat goal is reached (for now only
  //  // uncertainty goal)
  //  goalUncertainty = DictGetDouble(user_info, "goal_uncertainty");
  threshEdepPerc = DictGetDouble(user_info, "thresh_voxel_edep_for_unc_calc");

  // translation
  fTranslation = DictGetG4ThreeVector(user_info, "translation");
  // Hit type (random, pre, post etc)
  fHitType = DictGetStr(user_info, "hit_type");
  //  // Option: make a copy of the image for each thread, instead of writing on
  //  // same image
  //  fcpImageForThreadsFlag = DictGetBool(user_info, "use_more_ram");
  //  // Option: calculate the standard error of the mean
  //  fSTEofMeanFlag = DictGetBool(user_info, "ste_of_mean");
}

void GateDoseActor::InitializeCpp() {
  NbOfThreads = G4Threading::GetNumberOfRunningWorkerThreads();

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
  NbOfEvent = 0;

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
                                           int numberOfVoxels) {
  data.squared_worker_flatimg.resize(numberOfVoxels);
  std::fill(data.squared_worker_flatimg.begin(),
            data.squared_worker_flatimg.end(), 0.0);
  data.lastid_worker_flatimg.resize(numberOfVoxels);
  std::fill(data.lastid_worker_flatimg.begin(),
            data.lastid_worker_flatimg.end(), 0);
}

void GateDoseActor::BeginOfRunAction(const G4Run *run) {
  int N_voxels = size_edep[0] * size_edep[1] * size_edep[2];
  if (fEdepSquaredFlag) {
    PrepareLocalDataForRun(fThreadLocalDataEdep.Get(), N_voxels);
  }
  if (fDoseSquaredFlag) {
    PrepareLocalDataForRun(fThreadLocalDataDose.Get(), N_voxels);
  }
}

void GateDoseActor::BeginOfEventAction(const G4Event *event) {
  G4AutoLock mutex(&SetNbEventMutex);
  NbOfEvent++;
}

void GateDoseActor::SteppingAction(G4Step *step) {
  auto preGlobal = step->GetPreStepPoint()->GetPosition();
  auto postGlobal = step->GetPostStepPoint()->GetPosition();
  auto touchable = step->GetPreStepPoint()->GetTouchable();

  // FIXME If the volume has multiple copy, touchable->GetCopyNumber(0) ?
  // consider random position between pre and post
  auto position = postGlobal;
  if (fHitType == "pre") {
    position = preGlobal;
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

  Image3DType::IndexType index;
  bool isInside = cpp_edep_image->TransformPhysicalPointToIndex(point, index);

  // set value
  if (isInside) {

    // get edep in MeV (take weight into account)
    auto w = step->GetTrack()->GetWeight();
    auto edep = step->GetTotalEnergyDeposit() / CLHEP::MeV * w;
    double density;
    double dose;

    if (fToWaterFlag) {
      auto *current_material = step->GetPreStepPoint()->GetMaterial();
      double dedx_cut = DBL_MAX;
      // dedx
      double dedx_currstep = 0., dedx_water = 0.;
      // other material
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

    ImageAddValue<Image3DType>(cpp_edep_image, index, edep);

    if (fDoseFlag || fDoseSquaredFlag) {
      double density;
      if (fToWaterFlag) {
        auto *water =
            G4NistManager::Instance()->FindOrBuildMaterial("G4_WATER");
        density = water->GetDensity();
      } else {
        auto *current_material = step->GetPreStepPoint()->GetMaterial();
        density = current_material->GetDensity();
      }
      dose = edep / density;
      if (fDoseFlag) {
        ImageAddValue<Image3DType>(cpp_dose_image, index, dose);
      }
    }

    if (fCountsFlag) {
      ImageAddValue<Image3DType>(cpp_counts_image, index, 1);
    }
    if (fEdepSquaredFlag || fDoseSquaredFlag) {
      auto event_id =
          G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
      if (fEdepSquaredFlag) {
        //        G4AutoLock mutex(&SetPixelMutex);
        ScoreSquaredValue(fThreadLocalDataEdep.Get(), cpp_edep_squared_image,
                          edep, event_id, index);
      }
      if (fDoseSquaredFlag) {
        //        G4AutoLock mutex(&SetPixelMutex);
        ScoreSquaredValue(fThreadLocalDataDose.Get(), cpp_dose_squared_image,
                          dose, event_id, index);
      }
    }
  } // else: outside of the image
}

double GateDoseActor::ComputeMeanUncertainty() {
  G4AutoLock mutex(&ComputeUncertaintyMutex);
  itk::ImageRegionIterator<Image3DType> edep_iterator3D(
      cpp_edep_image, cpp_edep_image->GetLargestPossibleRegion());
  double mean_unc = 0.0;
  int n_voxel_unc = 0;
  double n = 2.0;
  n = NbOfEvent;

  if (n < 2.0) {
    n = 2.0;
  }
  double max_edep = GetMaxValueOfImage(cpp_edep_image);

  for (edep_iterator3D.GoToBegin(); !edep_iterator3D.IsAtEnd();
       ++edep_iterator3D) {
    Image3DType::IndexType index_f = edep_iterator3D.GetIndex();
    double val = cpp_edep_image->GetPixel(index_f);

    if (val > max_edep * threshEdepPerc) {
      val /= n;
      n_voxel_unc++;
      double val_squared_mean = cpp_edep_squared_image->GetPixel(index_f) / n;

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
  std::cout << "unc: " << mean_unc << std::endl;
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

  if (fEdepSquaredFlag) {
    GateDoseActor::FlushSquaredValue(fThreadLocalDataEdep.Get(),
                                     cpp_edep_squared_image);
  }
  if (fDoseSquaredFlag) {
    GateDoseActor::FlushSquaredValue(fThreadLocalDataDose.Get(),
                                     cpp_dose_squared_image);
  }
}

void GateDoseActor::ScoreSquaredValue(threadLocalT &data,
                                      Image3DType::Pointer cpp_image,
                                      double value, int event_id,
                                      Image3DType::IndexType index) {
  G4AutoLock mutex(&SetPixelMutex);
  int index_flat = sub2ind(index);
  auto previous_id = data.lastid_worker_flatimg[index_flat];
  data.lastid_worker_flatimg[index_flat] = event_id;
  if (event_id == previous_id) {
    // Same event: sum the deposited value associated with this event ID
    // and square once a new event ID is found (case below)
    data.squared_worker_flatimg[index_flat] += value;
  } else {
    // Different event : square deposited quantity from the last event ID
    // and start accumulating deposited quantity for this new event ID
    auto v = data.squared_worker_flatimg[index_flat];
    ImageAddValue<Image3DType>(cpp_image, index, v * v);
    // new temp value
    data.squared_worker_flatimg[index_flat] = value;
  }
}

void GateDoseActor::FlushSquaredValue(threadLocalT &data,
                                      Image3DType::Pointer cpp_image) {
  //  G4AutoLock mutex(&SetWorkerEndRunMutex);

  itk::ImageRegionIterator<Image3DType> iterator3D(
      cpp_image, cpp_image->GetLargestPossibleRegion());
  for (iterator3D.GoToBegin(); !iterator3D.IsAtEnd(); ++iterator3D) {
    Image3DType::IndexType index_f = iterator3D.GetIndex();
    Image3DType::PixelType pixelValue3D =
        data.squared_worker_flatimg[sub2ind(index_f)];
    ImageAddValue<Image3DType>(cpp_image, index_f, pixelValue3D * pixelValue3D);
  }
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
