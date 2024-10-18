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
  // Action for this actor: during stepping
  //  fActions.insert("SteppingAction");
  //  fActions.insert("BeginOfRunAction");
  //  fActions.insert("EndOfRunAction");
  //  fActions.insert("BeginOfEventAction");
  // fActions.insert("EndOfSimulationWorkerAction");
  // fActions.insert("EndSimulationAction");
  // fActions.insert("EndOfEventAction");
}

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
  goalUncertainty = DictGetDouble(user_info, "goal_uncertainty");
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

  if (fSquareFlag) {
    cpp_square_image = Image3DType::New();
  }
  if (fDensityFlag) {
    cpp_density_image = Image3DType::New();
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

  if (fSquareFlag) {
    AttachImageToVolume<Image3DType>(cpp_square_image, fPhysicalVolumeName,
                                     fTranslation);
  }
  if (fDensityFlag) {
    AttachImageToVolume<Image3DType>(cpp_density_image, fPhysicalVolumeName,
                                     fTranslation);
  }
}

void GateDoseActor::BeginOfRunAction(const G4Run *run) {
  if (fSquareFlag) {
    int N_voxels = size_edep[0] * size_edep[1] * size_edep[2];
    auto &l = fThreadLocalData.Get();
    l.edepSquared_worker_flatimg.resize(N_voxels);
    std::fill(l.edepSquared_worker_flatimg.begin(),
              l.edepSquared_worker_flatimg.end(), 0.0);
    l.lastid_worker_flatimg.resize(N_voxels);
    std::fill(l.lastid_worker_flatimg.begin(), l.lastid_worker_flatimg.end(),
              0);
  }

  //  if (fcpImageForThreadsFlag && (run->GetRunID() < 1)) {
  //    l.edep_worker_flatimg.resize(N_voxels);
  //    std::fill(l.edep_worker_flatimg.begin(), l.edep_worker_flatimg.end(),
  //    0.0);
  //  }
}

void GateDoseActor::BeginOfEventAction(const G4Event *event) {
  G4AutoLock mutex(&SetNbEventMutex);
  NbOfEvent++;
  //  threadLocalT &data = fThreadLocalData.Get();
  //  data.NbOfEvent_worker++;
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
      auto &emc = fThreadLocalData.Get().emcalc;
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

    if (fDensityFlag) {
      // FIXME : not very efficient: should be computed once for all
      auto *current_material = step->GetPreStepPoint()->GetMaterial();
      auto density = current_material->GetDensity();
      cpp_density_image->SetPixel(index, density);
    }

    if (fSquareFlag) {
      auto &locald = fThreadLocalData.Get();
      G4AutoLock mutex(&SetPixelMutex);

      int index_flat = sub2ind(index);
      auto event_id =
          G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
      auto previous_id = locald.lastid_worker_flatimg[index_flat];
      locald.lastid_worker_flatimg[index_flat] = event_id;
      if (event_id == previous_id) {
        // Same event: sum the deposited energy associated with this event ID
        // and square once a new event ID is found (case below)
        locald.edepSquared_worker_flatimg[index_flat] += edep;
      } else {
        // Different event : square deposited energy from the last event ID
        // and start accumulating deposited energy for this new event ID
        auto e = locald.edepSquared_worker_flatimg[index_flat];
        ImageAddValue<Image3DType>(cpp_square_image, index, e * e);
        // new temp value
        locald.edepSquared_worker_flatimg[index_flat] = edep;
      }
    }
  } // else: outside of the image
}

// void GateDoseActor::EndSimulationAction() {
//    double planned_NbOfEvent_per_worker = double(NbOfEvent / (NbOfThreads));
//    if (fSTEofMeanFlag) {
//      itk::ImageRegionIterator<Image3DType> edep_iterator3D(
//          cpp_edep_image, cpp_edep_image->GetLargestPossibleRegion());
//      for (edep_iterator3D.GoToBegin(); !edep_iterator3D.IsAtEnd();
//           ++edep_iterator3D) {
//
//        Image3DType::IndexType index_f = edep_iterator3D.GetIndex();
//        Image3DType::PixelType pixelValue3D_perEvent =
//            cpp_square_image->GetPixel(index_f);
//
//        Image3DType::PixelType pixelValue_cpp =
//            pixelValue3D_perEvent * planned_NbOfEvent_per_worker;
//        cpp_square_image->SetPixel(index_f, pixelValue_cpp);
//        // std::cout << "PixelValue end: " << pixelValue_cpp << std::endl;
//      }
//    }
//}

void GateDoseActor::EndOfEventAction(const G4Event *event) {
    // flush thread local data into global image (postponed for now)

    // if the user didn't set uncertainty goal, do nothing
    if (goalUncertainty == 0){return;}

    // check if we reached the Nb of events for next evaluation
    if (NbOfEvent >= NbEventsNextCheck){
        // get thread idx. Ideally, only one thread should do the uncertainty calculation
        // don't ask for thread idx if no MT
        if (!G4Threading::IsMultithreadedApplication() ||
            G4Threading::G4GetThreadId() == 0) {
            // check stop criteria
            double UncCurrent = ComputeMeanUncertainty();
            if (UncCurrent <= goalUncertainty){
                fStopRunFlag = true;
            }
            else{
                // estimate Nevents at which next check should occour
                NbEventsNextCheck = (UncCurrent/goalUncertainty)*(UncCurrent/goalUncertainty)*NbOfEvent*1.05;
            }
        }
        // since there is one source manager per thread, we need all threads to send the termination signal
        if (fStopRunFlag){
            fSourceManager->SetRunTerminationFlag(true);
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
  //  if (fcpImageForThreadsFlag) {
  //    n = NbOfThreads;
  //  } else {
  //    n = NbOfEvent;
  //  }
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
      double val_squared_mean = cpp_square_image->GetPixel(index_f) / n;

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

  if (fSquareFlag) {
    // We need to flush the energy deposit from the last event ID of this run
    // to cpp_square_image because it has only been accumulated in the
    // SteppingAction It would be flushed to cpp_square_image in the
    // SteppingAction of the next event ID, but we are at the end of the run.
    threadLocalT &data = fThreadLocalData.Get();

    G4AutoLock mutex(&SetWorkerEndRunMutex);

    itk::ImageRegionIterator<Image3DType> iterator3D(
        cpp_square_image, cpp_square_image->GetLargestPossibleRegion());
    for (iterator3D.GoToBegin(); !iterator3D.IsAtEnd(); ++iterator3D) {
      Image3DType::IndexType index_f = iterator3D.GetIndex();
      Image3DType::PixelType pixelValue3D =
          data.edepSquared_worker_flatimg[sub2ind(index_f)];
      ImageAddValue<Image3DType>(cpp_square_image, index_f,
                                 pixelValue3D * pixelValue3D);
    }
  }
}

int GateDoseActor::EndOfRunActionMasterThread(int run_id) {
  //  if (goalUncertainty != 0.0) {
  //    double unc = ComputeMeanUncertainty();
  //    if (unc <= goalUncertainty) {
  //      return 1;
  //    } else {
  //      return 0;
  //    }
  //  } else {
  //    return 0;
  //  }
  return 0;
}

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

  //   while (!pq.empty()) {
  //         std::cout << pq.top() << " ";
  //         pq.pop();
  //     }
  return max;
}
