/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateDoseActor.h"
#include "G4MTRunManager.hh"
#include "G4Navigator.hh"
#include "G4RandomTools.hh"
#include "G4RunManager.hh"
#include "G4Threading.hh"
#include "G4ios.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"
#include "itkAddImageFilter.h"
#include <iostream>
#include <itkImageRegionIterator.h>

#include "G4Electron.hh"
#include "G4EmCalculator.hh"
#include "G4Gamma.hh"
#include "G4MaterialTable.hh"
#include "G4NistManager.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleTable.hh"

// Mutex that will be used by thread to write in the edep/dose image
G4Mutex SetPixelMutex = G4MUTEX_INITIALIZER;
G4Mutex SetNbEventMutex = G4MUTEX_INITIALIZER;

GateDoseActor::GateDoseActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  // Create the image pointer
  // (the size and allocation will be performed on the py side)
  cpp_edep_image = Image3DType::New();
  // Action for this actor: during stepping
  fActions.insert("SteppingAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("EndSimulationAction");
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
  if (fUncertaintyFlag || fSquareFlag || fSTEofMeanFlag) {
    if (NbOfThreads == 0) {
      NbOfThreads = 1;
    }
    cpp_square_image = Image3DType::New();
    if (fUncertaintyFlag || fSquareFlag) {
      cpp_4D_last_id_image = ImageInt4DType::New();
      cpp_4D_temp_image = Image4DType::New();
    }
  }
  if (fDoseFlag || fDoseToWaterFlag) {
    cpp_dose_image = Image3DType::New();
  }
  if (fcpImageForThreadsFlag) {
    cpp_4D_temp_dose_image = Image4DType::New();
  }
}

void GateDoseActor::BeginOfRunAction(const G4Run *) {

  Image3DType::RegionType region = cpp_edep_image->GetLargestPossibleRegion();
  size_edep = region.GetSize();
  if (fUncertaintyFlag || fSquareFlag) {
    size_4D[0] = size_edep[0];
    size_4D[1] = size_edep[1];
    size_4D[2] = size_edep[2];
    size_4D[3] = NbOfThreads;

    cpp_4D_last_id_image->SetRegions(size_4D);
    cpp_4D_last_id_image->Allocate();

    cpp_4D_temp_image->SetRegions(size_4D);
    cpp_4D_temp_image->Allocate();
  }
  if (fcpImageForThreadsFlag) {
    size_4D[0] = size_edep[0];
    size_4D[1] = size_edep[1];
    size_4D[2] = size_edep[2];
    size_4D[3] = NbOfThreads;

    cpp_4D_temp_dose_image->SetRegions(size_4D);
    cpp_4D_temp_dose_image->Allocate();
  }

  // Important ! The volume may have moved, so we re-attach each run
  AttachImageToVolume<Image3DType>(cpp_edep_image, fPhysicalVolumeName,
                                   fInitialTranslation);
  // compute volume of a dose voxel
  auto sp = cpp_edep_image->GetSpacing();
  fVoxelVolume = sp[0] * sp[1] * sp[2];
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

  // get edep in MeV (take weight into account)
  auto w = step->GetTrack()->GetWeight();
  auto edep = step->GetTotalEnergyDeposit() / CLHEP::MeV * w;

  // get pixel index
  Image3DType::IndexType index;
  Image4DType::IndexType Threadindex;
  bool isInside = cpp_edep_image->TransformPhysicalPointToIndex(point, index);

  // set value
  if (isInside) {
    // if (!fcpImageForThreadsFlag) {
    G4AutoLock mutex(&SetPixelMutex);
    // std::cout<<"lol"<<std::endl;

    // If uncertainty: consider edep per event
    if (fUncertaintyFlag || fSquareFlag) {
      auto event_id =
          G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
      Threadindex[0] = index[0];
      Threadindex[1] = index[1];
      Threadindex[2] = index[2];
      if (NbOfThreads == 1) {
        Threadindex[3] = 0;
      } else {
        Threadindex[3] = G4Threading::G4GetThreadId();
      }
      auto previous_id = cpp_4D_last_id_image->GetPixel(Threadindex);
      cpp_4D_last_id_image->SetPixel(Threadindex, event_id);
      if (event_id == previous_id) {
        // Same event : continue temporary edep
        ImageAddValue<Image4DType>(cpp_4D_temp_image, Threadindex, edep);
      } else {
        // Different event : update previous and start new event
        auto e = cpp_4D_temp_image->GetPixel(Threadindex);
        ImageAddValue<Image3DType>(cpp_square_image, index, e * e);
        // new temp value
        cpp_4D_temp_image->SetPixel(Threadindex, edep);
      }
    }
    if (fcpImageForThreadsFlag) {
      Threadindex[0] = index[0];
      Threadindex[1] = index[1];
      Threadindex[2] = index[2];
      if (NbOfThreads == 1) {
        Threadindex[3] = 0;
      } else {
        Threadindex[3] = G4Threading::G4GetThreadId();
      }
      ImageAddValue<Image4DType>(cpp_4D_temp_dose_image, Threadindex, edep);

    } else {
      ImageAddValue<Image3DType>(cpp_edep_image, index, edep);
    }
    // Compute the dose in Gray
    if (fDoseFlag || fDoseToWaterFlag) {
      auto *current_material = step->GetPreStepPoint()->GetMaterial();
      auto density = current_material->GetDensity();
      auto dose = edep / density / fVoxelVolume / CLHEP::gray;
      if (fDoseToWaterFlag) {
        double dedx_cut = DBL_MAX;
        // dedx
        double dedx_currstep = 0., dedx_water = 0.;
        double density_water = 1.0;
        // other material
        const G4ParticleDefinition *p =
            step->GetTrack()->GetParticleDefinition();
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
        auto &l = fThreadLocalData.Get().emcalc;

        dedx_currstep =
            l.ComputeTotalDEDX(energy, p, current_material, dedx_cut);
        dedx_water = l.ComputeTotalDEDX(energy, p, water, dedx_cut);
        // dedx_currstep =
        //     emcalc->ComputeTotalDEDX(energy, p, material_currstep, dedx_cut);
        // dedx_water = emcalc->ComputeTotalDEDX(energy, p, water, dedx_cut);
        density_water = water->GetDensity();
        // double spr = dedx_currstep / dedx_water;
        // double mspr = (density / density_water) * (dedx_water /
        // dedx_currstep); std::cout <<"density_currstep: " << density_currstep
        //  *(CLHEP::g/CLHEP::cm3)<< spr<< std::endl;
        /*
        std::cout <<"------------------" << std::endl;
        std::cout <<"water name: " <<water->GetName() << std::endl;
        std::cout <<"water getDensity: " <<water->GetDensity() << std::endl;
        std::cout <<"mat name: " << current_material->GetName() << std::endl;
        std::cout <<"matdensity: " << current_material->GetDensity() <<
        std::endl; std::cout
        <<"density: " << density << std::endl; std::cout
        <<"SPR: " << spr<< std::endl; std::cout <<"mSPR: " << 1/mspr<<
        std::endl;
        */

        // In current implementation, dose deposited directly by neutrons is
        // neglected - the below lines prevent "inf or NaN"
        if (dedx_currstep == 0 || dedx_water == 0) {
          dose = 0.;
        } else {
          // std::cout << "Overwrite dose: "<< std::endl;
          // std::cout << "Dose before: "<< dose << std::endl;
          dose *= (density / density_water) * (dedx_water / dedx_currstep);
          // std::cout << "Dose after: "<< dose << std::endl<< std::endl;
        }
      } // end dose to water
      ImageAddValue<Image3DType>(cpp_dose_image, index, dose);
    } // end if DoseFlag
  }   // else : outside the image
}

void GateDoseActor::EndSimulationAction() {

  if (fUncertaintyFlag || fSquareFlag) {

    // Take the square of the 4D temp image
    itk::ImageRegionIterator<Image4DType> iterator_temp(
        cpp_4D_temp_image, cpp_4D_temp_image->GetLargestPossibleRegion());
    for (iterator_temp.GoToBegin(); !iterator_temp.IsAtEnd(); ++iterator_temp) {
      Image4DType::PixelType pixel_temp = iterator_temp.Get();
      iterator_temp.Set(pixel_temp * pixel_temp);
    }

    // Create a 3D image from the 4D image where the pixel corresponding to the
    // same threadID are summed.

    itk::ImageRegionIterator<Image3DType> iterator3D(
        cpp_square_image, cpp_square_image->GetLargestPossibleRegion());
    for (iterator3D.GoToBegin(); !iterator3D.IsAtEnd(); ++iterator3D) {
      Image3DType::PixelType pixelValue3D = 0;
      for (int i = 0; i < NbOfThreads; ++i) {
        Image4DType::IndexType index_f;
        index_f[0] = iterator3D.GetIndex()[0];
        index_f[1] = iterator3D.GetIndex()[1];
        index_f[2] = iterator3D.GetIndex()[2];
        index_f[3] = i;
        pixelValue3D += cpp_4D_temp_image->GetPixel(index_f);
      }
      ImageAddValue<Image3DType>(cpp_square_image, iterator3D.GetIndex(),
                                 pixelValue3D);
    }
  }

  if (fcpImageForThreadsFlag) {

    itk::ImageRegionIterator<Image3DType> edep_iterator3D(
        cpp_edep_image, cpp_edep_image->GetLargestPossibleRegion());
    for (edep_iterator3D.GoToBegin(); !edep_iterator3D.IsAtEnd();
         ++edep_iterator3D) {
      Image3DType::PixelType pixelValue3D = 0;
      for (int i = 0; i < NbOfThreads; ++i) {
        Image4DType::IndexType index_f;
        index_f[0] = edep_iterator3D.GetIndex()[0];
        index_f[1] = edep_iterator3D.GetIndex()[1];
        index_f[2] = edep_iterator3D.GetIndex()[2];
        index_f[3] = i;
        pixelValue3D += cpp_4D_temp_dose_image->GetPixel(index_f);
      }
      cpp_edep_image->SetPixel(edep_iterator3D.GetIndex(), pixelValue3D);
    }
  }
  if (fSTEofMeanFlag) {
    double N_samples = (double)NbOfThreads;
    double sample_diff = 0.;
    itk::ImageRegionIterator<Image3DType> ste_iterator3D(
        cpp_square_image, cpp_square_image->GetLargestPossibleRegion());
    for (ste_iterator3D.GoToBegin(); !ste_iterator3D.IsAtEnd();
         ++ste_iterator3D) {
      Image3DType::PixelType pixelValue3D = 0;

      double sample_mean =
          0.0 * (cpp_edep_image->GetPixel(ste_iterator3D.GetIndex())) /
          NbOfThreads;
      for (int i = 0; i < NbOfThreads; ++i) {
        Image4DType::IndexType index_f;
        index_f[0] = ste_iterator3D.GetIndex()[0];
        index_f[1] = ste_iterator3D.GetIndex()[1];
        index_f[2] = ste_iterator3D.GetIndex()[2];
        index_f[3] = i;
        /*std::cout << "Pixel i: " << cpp_4D_temp_dose_image->GetPixel(index_f)
                  << std::endl; */
        sample_diff = cpp_4D_temp_dose_image->GetPixel(index_f) - sample_mean;
        pixelValue3D += (sample_diff * sample_diff);
      }
      cpp_square_image->SetPixel(ste_iterator3D.GetIndex(), pixelValue3D);
      // std::cout << "PixelValue 3D: " << pixelValue3D << std::endl;
    }
  }
}
