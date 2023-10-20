/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "G4Navigator.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "G4Threading.hh"

#include "GateDoseActor.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

#include <iostream>
#include <itkAddImageFilter.h>
#include <itkImageRegionIterator.h>

#include "G4Electron.hh"
#include "G4EmCalculator.hh"
#include "G4Gamma.hh"
#include "G4MaterialTable.hh"
#include "G4NistManager.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleTable.hh"

// Mutex that will be used by thread to write in the edep/dose image
G4Mutex SetWorkerEndRunMutex = G4MUTEX_INITIALIZER;
G4Mutex SetPixelMutex = G4MUTEX_INITIALIZER;
// G4Mutex SetNbEventMutex = G4MUTEX_INITIALIZER;

GateDoseActor::GateDoseActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  // Create the image pointer
  // (the size and allocation will be performed on the py side)
  cpp_edep_image = Image3DType::New();
  // Action for this actor: during stepping
  fActions.insert("SteppingAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("EndOfSimulationWorkerAction");
  fActions.insert("EndSimulationAction");
  fActions.insert("EndOfRunAction");
  // Option: compute uncertainty
  fUncertaintyFlag = DictGetBool(user_info, "uncertainty");
  // Option: compute square
  fSquareFlag = DictGetBool(user_info, "square");
  // Option: compute dose in Gray
  fDoseFlag = DictGetBool(user_info, "dose");
  // Option: compute dose to water
  fDoseToWaterFlag = DictGetBool(user_info, "dose_to_water");
  // translation
  fInitialTranslation = DictGetG4ThreeVector(user_info, "translation");
  // Hit type (random, pre, post etc)
  fHitType = DictGetStr(user_info, "hit_type");
  // Option: make a copy of the image for each thread, instead of writing on
  // same image
  fcpImageForThreadsFlag = DictGetBool(user_info, "use_more_RAM");
  // Option: calculate the standard error of the mean
  fSTEofMeanFlag = DictGetBool(user_info, "ste_of_mean");
}

void GateDoseActor::ActorInitialize() {
  NbOfThreads = G4Threading::GetNumberOfRunningWorkerThreads();

  if (fUncertaintyFlag) {
    fSquareFlag = true;
  }
  if (fSquareFlag || fSTEofMeanFlag) {
    cpp_square_image = Image3DType::New();
  }

  if (fDoseToWaterFlag) {
    // to assure it is enabled and not need to ask both conditions on the fly in
    // stepping action
    fDoseFlag = true;
  }
}

void GateDoseActor::BeginOfRunAction(const G4Run *run) {

  Image3DType::RegionType region = cpp_edep_image->GetLargestPossibleRegion();
  size_edep = region.GetSize();

  // Important ! The volume may have moved, so we re-attach each run
  AttachImageToVolume<Image3DType>(cpp_edep_image, fPhysicalVolumeName,
                                   fInitialTranslation);
  // compute volume of a dose voxel
  auto sp = cpp_edep_image->GetSpacing();
  fVoxelVolume = sp[0] * sp[1] * sp[2];
  int N_voxels = size_edep[0] * size_edep[1] * size_edep[2];
  auto &l = fThreadLocalData.Get();
  if (fSquareFlag || fSTEofMeanFlag) {
    cpp_square_image->SetRegions(size_edep);
    cpp_square_image->Allocate();
  }
  if (fSquareFlag && run->GetRunID() < 1) {
    l.edepSquared_worker_flatimg.resize(N_voxels);
    std::fill(l.edepSquared_worker_flatimg.begin(),
              l.edepSquared_worker_flatimg.end(), 0.0);

    l.lastid_worker_flatimg.resize(N_voxels);
    std::fill(l.lastid_worker_flatimg.begin(), l.lastid_worker_flatimg.end(),
              0);
  }
  if (fcpImageForThreadsFlag && run->GetRunID() < 1) {
    l.edep_worker_flatimg.resize(N_voxels);
    std::fill(l.edep_worker_flatimg.begin(), l.edep_worker_flatimg.end(), 0.0);
  }
}

void GateDoseActor::BeginOfEventAction(const G4Event *event) {
  // G4AutoLock mutex(&SetNbEventMutex);
  // NbOfEvent++;
  threadLocalT &data = fThreadLocalData.Get();
  data.NbOfEvent_worker++;
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

  // get edep in MeV (take weight into account)
  auto w = step->GetTrack()->GetWeight();
  auto edep = step->GetTotalEnergyDeposit() / CLHEP::MeV * w;
  auto scoring_quantity = edep;

  // Compute the dose in Gray
  if (fDoseFlag) {
    auto *current_material = step->GetPreStepPoint()->GetMaterial();
    auto density = current_material->GetDensity();
    auto dose = edep / density / fVoxelVolume / CLHEP::gray;
    if (fDoseToWaterFlag) {
      /*
       * This is a one to one copy from Gate 9.3; Improvements highly welcome
       */
      double dedx_cut = DBL_MAX;
      // dedx
      double dedx_currstep = 0., dedx_water = 0.;
      double density_water = 1.0;
      // other material
      const G4ParticleDefinition *p = step->GetTrack()->GetParticleDefinition();
      static G4Material *water =
          G4NistManager::Instance()->FindOrBuildMaterial("G4_WATER");
      auto energy1 = step->GetPreStepPoint()->GetKineticEnergy();
      auto energy2 = step->GetPostStepPoint()->GetKineticEnergy();
      auto energy = (energy1 + energy2) / 2;
      // Accounting for particles with dedx=0; i.e. gamma and neutrons
      // For gamma we consider the dedx of electrons instead - testing
      // with 1.3 MeV photon beam or 150 MeV protons or 1500 MeV carbon ion
      // beam showed that the error induced is 0 		when comparing
      // dose and dosetowater in the material G4_WATER For neutrons the dose
      // is neglected - testing with 1.3 MeV photon beam or 150 MeV protons or
      // 1500 MeV carbon ion beam showed that the error induced is < 0.01%
      //		when comparing dose and dosetowater in the material
      // G4_WATER (we are systematically missing a little bit of dose of
      // course with this solution)

      if (p == G4Gamma::Gamma())
        p = G4Electron::Electron();
      auto &emc = fThreadLocalData.Get().emcalc;

      dedx_currstep =
          emc.ComputeTotalDEDX(energy, p, current_material, dedx_cut);
      dedx_water = emc.ComputeTotalDEDX(energy, p, water, dedx_cut);
      // dedx_currstep =
      //   emcalc->ComputeTotalDEDX(energy, p, material_currstep, dedx_cut);
      // dedx_water = emcalc->ComputeTotalDEDX(energy, p, water, dedx_cut);
      density_water = water->GetDensity();
      // double spr = dedx_currstep / dedx_water;
      // double mspr = (density / density_water) * (dedx_water /
      // dedx_currstep); std::cout <<"density_currstep: " << density_currstep
      //  *(CLHEP::g/CLHEP::cm3)<< spr<< std::endl;

      // In current implementation, dose deposited directly by neutrons is
      // neglected - the below lines prevent "inf or NaN"
      if (dedx_currstep == 0 || dedx_water == 0) {
        dose = 0.;
      } else {
        dose *= (density / density_water) * (dedx_water / dedx_currstep);
      }
    } // end dose to water
    scoring_quantity = dose;
  } // end if DoseFlag

  Image3DType::IndexType index;
  bool isInside = cpp_edep_image->TransformPhysicalPointToIndex(point, index);

  // set value
  if (isInside) {
    int index_flat = sub2ind(index);

    auto &locald = fThreadLocalData.Get();
    if (fcpImageForThreadsFlag) {

      locald.edep_worker_flatimg[index_flat] += scoring_quantity;

    } else {
      G4AutoLock mutex(&SetPixelMutex);

      ImageAddValue<Image3DType>(cpp_edep_image, index, scoring_quantity);
      // If uncertainty: consider edep per event
      if (fSquareFlag) {
        auto event_id =
            G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
        auto previous_id = locald.lastid_worker_flatimg[index_flat];
        locald.lastid_worker_flatimg[index_flat] = event_id;
        if (event_id == previous_id) {
          // Same event : continue temporary edep
          locald.edepSquared_worker_flatimg[index_flat] += scoring_quantity;
        } else {
          // Different event : update previoupyths and start new event
          auto e = locald.edepSquared_worker_flatimg[index_flat];
          ImageAddValue<Image3DType>(cpp_square_image, index, e * e);
          // new temp value
          locald.edepSquared_worker_flatimg[index_flat] = scoring_quantity;
        }
      }
    } // else : outside the image
  }
}

void GateDoseActor::EndSimulationAction() {
  double planned_NbOfEvent_per_worker = double(NbOfEvent / (NbOfThreads));
  if (fSTEofMeanFlag) {
    itk::ImageRegionIterator<Image3DType> edep_iterator3D(
        cpp_edep_image, cpp_edep_image->GetLargestPossibleRegion());
    for (edep_iterator3D.GoToBegin(); !edep_iterator3D.IsAtEnd();
         ++edep_iterator3D) {

      Image3DType::IndexType index_f = edep_iterator3D.GetIndex();
      Image3DType::PixelType pixelValue3D_perEvent =
          cpp_square_image->GetPixel(index_f);

      Image3DType::PixelType pixelValue_cpp =
          pixelValue3D_perEvent * planned_NbOfEvent_per_worker;
      cpp_square_image->SetPixel(index_f, pixelValue_cpp);
      // std::cout << "PixelValue end: " << pixelValue_cpp << std::endl;
    }
  }
}

void GateDoseActor::EndOfSimulationWorkerAction(const G4Run * /*lastRun*/) {
  //  Called every time the simulation is about to end, by ALL threads
  //  So, the data are merged (need a mutex lock)
  G4AutoLock mutex(&SetWorkerEndRunMutex);
  threadLocalT &data = fThreadLocalData.Get();
  NbOfEvent += data.NbOfEvent_worker;
  // merge all threads (need mutex)
  // fCounts["run_count"] += data.fRunCount;
  if (fcpImageForThreadsFlag) {

    itk::ImageRegionIterator<Image3DType> edep_iterator3D(
        cpp_edep_image, cpp_edep_image->GetLargestPossibleRegion());
    for (edep_iterator3D.GoToBegin(); !edep_iterator3D.IsAtEnd();
         ++edep_iterator3D) {

      Image3DType::IndexType index_f = edep_iterator3D.GetIndex();
      Image3DType::PixelType pixelValue3D =
          data.edep_worker_flatimg[sub2ind(index_f)];
      ImageAddValue<Image3DType>(cpp_edep_image, edep_iterator3D.GetIndex(),
                                 pixelValue3D);
      if (fSTEofMeanFlag) {
        // Dividing by number of events/img for the unlikely event of having
        // different number of particles per thread. Probably not needeed.
        Image3DType::PixelType pixelValue_cpp =
            pixelValue3D * pixelValue3D / double(data.NbOfEvent_worker);
        ImageAddValue<Image3DType>(cpp_square_image, index_f, pixelValue_cpp);
      }
    }
  }
  if (fSquareFlag) {

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
  // std::cout << "This is the end, run "  << std::endl;
}
