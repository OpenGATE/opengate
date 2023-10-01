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
  fGrayFlag = DictGetBool(user_info, "gray");
  // translation
  fInitialTranslation = DictGetG4ThreeVector(user_info, "translation");
  // Hit type (random, pre, post etc)
  fHitType = DictGetStr(user_info, "hit_type");
}

void GateDoseActor::ActorInitialize() {
  if (fUncertaintyFlag || fSquareFlag) {
    NbOfThreads = G4Threading::GetNumberOfRunningWorkerThreads();
    if (NbOfThreads == 0) {
      NbOfThreads = 1;
    }
    cpp_4D_last_id_image = ImageInt4DType::New();
    cpp_4D_temp_image = Image4DType::New();
    cpp_square_image = Image3DType::New();
  }
  if (fGrayFlag) {
    cpp_dose_image = Image3DType::New();
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
    ImageAddValue<Image3DType>(cpp_edep_image, index, edep);

    // Compute the dose in Gray ?
    if (fGrayFlag) {
      auto *current_material = step->GetPreStepPoint()->GetMaterial();
      auto density = current_material->GetDensity();
      auto dose = edep / density / fVoxelVolume / CLHEP::gray;
      ImageAddValue<Image3DType>(cpp_dose_image, index, dose);
    }

  } // else : outside the image
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
}
