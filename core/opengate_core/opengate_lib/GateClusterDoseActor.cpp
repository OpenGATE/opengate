/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "G4Electron.hh"
#include "G4Gamma.hh"
#include "G4NistManager.hh"
#include "G4ParticleDefinition.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "G4Threading.hh"

#include "GateClusterDoseActor.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

#include <cmath>
#include <iostream>
#include <itkAddImageFilter.h>
#include <itkImageRegionIterator.h>
#include <queue>
#include <vector>

G4Mutex SetWorkerEndRunMutexClusterDoseActor = G4MUTEX_INITIALIZER;
G4Mutex SetPixelMutexClusterDoseActor = G4MUTEX_INITIALIZER;
G4Mutex ComputeUncertaintyMutexClusterDoseActor = G4MUTEX_INITIALIZER;
G4Mutex SetNbEventMutexClusterDoseActor = G4MUTEX_INITIALIZER;

GateClusterDoseActor::GateClusterDoseActor(py::dict &user_info)
    : GateVActor(user_info, true) {

  fUncertaintyGoal = 0.0;
  fThreshEdepPerc = 0.0;
  fOvershoot = 0.0;
  fNbEventsFirstCheck = 0;
  fNbEventsNextCheck = 0;
  fGoalUncertainty = 0.0;
  fNbOfEvent = 0;
}

void GateClusterDoseActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);

  fTranslation = DictGetG4ThreeVector(user_info, "translation");
  fHitType = DictGetStr(user_info, "hit_type");
}

void GateClusterDoseActor::InitializeCpp() {
  GateVActor::InitializeCpp();

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
  fScoreInOtherMaterial = (fScoreInMaterial == "material") ? false : true;

  if (fFastSPRCalcFlag) {
    auto material =
        G4NistManager::Instance()->FindOrBuildMaterial(fScoreInMaterial);
    fSPRCache.Initialize(material, fReferenceEnergySPR);
  }
}

void GateClusterDoseActor::BeginOfRunActionMasterThread(int run_id) {
  fNbOfEvent = 0;
  fNbEventsNextCheck = fNbEventsFirstCheck;

  AttachImageToVolume<Image3DType>(cpp_edep_image, fPhysicalVolumeName,
                                   fTranslation);
  auto sp = cpp_edep_image->GetSpacing();
  fVoxelVolume = sp[0] * sp[1] * sp[2];

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

void GateClusterDoseActor::PrepareLocalDataForRun(
    threadLocalT &data, const unsigned int numberOfVoxels) {
  data.squared_worker_flatimg.resize(numberOfVoxels);
  std::fill(data.squared_worker_flatimg.begin(),
            data.squared_worker_flatimg.end(), 0.0);
  data.lastid_worker_flatimg.resize(numberOfVoxels);
  std::fill(data.lastid_worker_flatimg.begin(),
            data.lastid_worker_flatimg.end(), 0);
}

void GateClusterDoseActor::BeginOfRunAction(const G4Run *run) {
  const auto N_voxels = size_edep[0] * size_edep[1] * size_edep[2];
  if (fEdepSquaredFlag) {
    PrepareLocalDataForRun(fThreadLocalDataEdep.Get(), N_voxels);
  }
  if (fDoseSquaredFlag) {
    PrepareLocalDataForRun(fThreadLocalDataDose.Get(), N_voxels);
  }
}

void GateClusterDoseActor::BeginOfEventAction(const G4Event *event) {
  G4AutoLock mutex(&SetNbEventMutexClusterDoseActor);
  fNbOfEvent++;
}

void GateClusterDoseActor::GetVoxelPosition(
    G4Step *step, G4ThreeVector &position, bool &isInside,
    Image3DType::IndexType &index) const {
  auto preGlobal = step->GetPreStepPoint()->GetPosition();
  auto postGlobal = step->GetPostStepPoint()->GetPosition();
  auto touchable = step->GetPreStepPoint()->GetTouchable();

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

  Image3DType::PointType point;
  point[0] = localPosition[0];
  point[1] = localPosition[1];
  point[2] = localPosition[2];

  isInside = cpp_edep_image->TransformPhysicalPointToIndex(point, index);
}

void GateClusterDoseActor::SteppingAction(G4Step *step) {
  const auto event_id =
      G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();

  G4ThreeVector position;
  bool isInside;
  Image3DType::IndexType index;
  GetVoxelPosition(step, position, isInside, index);

  if (isInside) {
    const auto w = step->GetTrack()->GetWeight();
    auto edep = step->GetTotalEnergyDeposit() / CLHEP::MeV * w;
    double dose;

    if (fScoreInOtherMaterial) {
      auto spr = CalculateSPR(step);
      edep *= spr;
    }

    if (fDoseFlag || fDoseSquaredFlag) {
      double density;
      if (fScoreInOtherMaterial) {
        const auto *material =
            G4NistManager::Instance()->FindOrBuildMaterial(fScoreInMaterial);
        density = material->GetDensity();
      } else {
        const auto *current_material = step->GetPreStepPoint()->GetMaterial();
        density = current_material->GetDensity();
      }
      dose = edep / density;
    }

    {
      G4AutoLock mutex(&SetPixelMutexClusterDoseActor);
      ImageAddValue<Image3DType>(cpp_edep_image, index, edep);
      if (fDoseFlag) {
        ImageAddValue<Image3DType>(cpp_dose_image, index, dose);
      }
      if (fCountsFlag) {
        ImageAddValue<Image3DType>(cpp_counts_image, index, 1);
      }
    }

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
  }
}

void GateClusterDoseActor::EndOfEventAction(const G4Event *event) {
  if (fUncertaintyGoal == 0) {
    return;
  }

  if (fNbOfEvent >= fNbEventsNextCheck) {
    if (fEdepSquaredFlag) {
      FlushSquaredValues(fThreadLocalDataEdep.Get(), cpp_edep_squared_image);
    }
    if (fDoseSquaredFlag) {
      FlushSquaredValues(fThreadLocalDataDose.Get(), cpp_dose_squared_image);
    }

    if (!G4Threading::IsMultithreadedApplication() ||
        G4Threading::G4GetThreadId() == 0) {
      double UncCurrent = ComputeMeanUncertainty();
      if (UncCurrent <= fUncertaintyGoal) {
        GateSourceManager::SetRunTerminationFlag(true);
      } else {
        fNbEventsNextCheck = static_cast<int>((UncCurrent / fUncertaintyGoal) *
                                              (UncCurrent / fUncertaintyGoal) *
                                              fNbOfEvent * fOvershoot);
      }
    }
  }
}

double GateClusterDoseActor::ComputeMeanUncertainty() {
  G4AutoLock mutex(&ComputeUncertaintyMutexClusterDoseActor);
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
        unc_i = 0.;
      }

      unc_i = sqrt(unc_i) / (val);

      if (unc_i > 1) {
        std::cout << "unc_i: " << unc_i << std::endl;
        std::cout << "edep: " << val << std::endl;
        std::cout << "edep_squared_mean: " << val_squared_mean << std::endl;
        unc_i = 1;
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

int GateClusterDoseActor::sub2ind(Image3DType::IndexType index3D) {
  return index3D[0] + size_edep[0] * (index3D[1] + size_edep[1] * index3D[2]);
}

void GateClusterDoseActor::ind2sub(int index_flat,
                                   Image3DType::IndexType &index3D) {
  int z = index_flat / (size_edep[0] * size_edep[1]);
  index_flat %= size_edep[0] * size_edep[1];
  int y = index_flat / size_edep[0];
  int x = index_flat % size_edep[0];
  index3D[0] = x;
  index3D[1] = y;
  index3D[2] = z;
}

void GateClusterDoseActor::EndOfRunAction(const G4Run *run) {
  if (fEdepSquaredFlag) {
    GateClusterDoseActor::FlushSquaredValues(fThreadLocalDataEdep.Get(),
                                             cpp_edep_squared_image);
  }
  if (fDoseSquaredFlag) {
    GateClusterDoseActor::FlushSquaredValues(fThreadLocalDataDose.Get(),
                                             cpp_dose_squared_image);
  }
}

void GateClusterDoseActor::ScoreSquaredValue(
    threadLocalT &data, const Image3DType::Pointer &cpp_image,
    const double value, const int event_id,
    const Image3DType::IndexType &index) {
  const int index_flat = sub2ind(index);
  const auto previous_id = data.lastid_worker_flatimg[index_flat];
  data.lastid_worker_flatimg[index_flat] = event_id;
  if (event_id == previous_id) {
    data.squared_worker_flatimg[index_flat] += value;
  } else {
    auto v = data.squared_worker_flatimg[index_flat];
    {
      G4AutoLock mutex(&SetPixelMutexClusterDoseActor);
      ImageAddValue<Image3DType>(cpp_image, index, v * v);
    }
    data.squared_worker_flatimg[index_flat] = value;
  }
}

void GateClusterDoseActor::FlushSquaredValues(
    threadLocalT &data, const Image3DType::Pointer &cpp_image) {
  G4AutoLock mutex(&SetPixelMutexClusterDoseActor);
  itk::ImageRegionIterator<Image3DType> iterator3D(
      cpp_image, cpp_image->GetLargestPossibleRegion());
  for (iterator3D.GoToBegin(); !iterator3D.IsAtEnd(); ++iterator3D) {
    Image3DType::IndexType index_f = iterator3D.GetIndex();
    Image3DType::PixelType pixelValue3D =
        data.squared_worker_flatimg[sub2ind(index_f)];
    ImageAddValue<Image3DType>(cpp_image, index_f, pixelValue3D * pixelValue3D);
  }
  const auto N_voxels = size_edep[0] * size_edep[1] * size_edep[2];
  PrepareLocalDataForRun(data, N_voxels);
}

int GateClusterDoseActor::EndOfRunActionMasterThread(int run_id) { return 0; }

double GateClusterDoseActor::GetMaxValueOfImage(Image3DType::Pointer imageP) {
  itk::ImageRegionIterator<Image3DType> iterator3D(
      imageP, imageP->GetLargestPossibleRegion());
  Image3DType::PixelType max = 0;
  Image3DType::IndexType index_max;
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

double GateClusterDoseActor::CalculateSPR(G4Step *step) {
  double spr = 0;
  G4double energy = 0;
  auto *current_material = step->GetPreStepPoint()->GetMaterial();
  const G4ParticleDefinition *p = step->GetTrack()->GetParticleDefinition();

  if (fFastSPRCalcFlag) {
    if (fTransitionEnergySPR == 0) {
      spr = fSPRCache.FindOrCalculateSPR(p, current_material);
      return spr;
    }
    auto energy1 = step->GetPreStepPoint()->GetKineticEnergy();
    auto energy2 = step->GetPostStepPoint()->GetKineticEnergy();
    energy = (energy1 + energy2) / 2;

    if (energy >= fTransitionEnergySPR) {
      spr = fSPRCache.FindOrCalculateSPR(p, current_material);
      return spr;
    }
  } else {
    auto energy1 = step->GetPreStepPoint()->GetKineticEnergy();
    auto energy2 = step->GetPostStepPoint()->GetKineticEnergy();
    energy = (energy1 + energy2) / 2;
  }

  double dedx_cut = DBL_MAX;
  double dedx_currstep = 0., dedx_material = 0.;
  static G4Material *material =
      G4NistManager::Instance()->FindOrBuildMaterial(fScoreInMaterial);
  if (p == G4Gamma::Gamma())
    p = G4Electron::Electron();
  auto &emc = fThreadLocalDataEdep.Get().emcalc;
  dedx_currstep = emc.ComputeTotalDEDX(energy, p, current_material, dedx_cut);
  dedx_material = emc.ComputeTotalDEDX(energy, p, material, dedx_cut);
  if (dedx_currstep != 0 || dedx_material != 0) {
    spr = dedx_material / dedx_currstep;
  }

  return spr;
}
