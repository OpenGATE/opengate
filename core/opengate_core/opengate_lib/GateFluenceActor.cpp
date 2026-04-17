/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "G4Navigator.hh"
#include "G4RunManager.hh"
#include "G4Threading.hh"
#include "GateActorManager.h"

#include "GateFluenceActor.h"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"

#include <iostream>
#include <itkAddImageFilter.h>
#include <itkImageRegionIterator.h>

// Mutex that will be used by thread to write the output image
G4Mutex SetPixelFluenceMutex = G4MUTEX_INITIALIZER;
G4Mutex SetNbEventMutexFluence = G4MUTEX_INITIALIZER;

GateFluenceActor::GateFluenceActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  fNbOfEvent = 0;
}

int GateFluenceActor::sub2ind(Image3DType::IndexType index3D) {
  return index3D[0] +
         size_region[0] * (index3D[1] + size_region[1] * index3D[2]);
}

void GateFluenceActor::FlushSquaredValues(
    threadLocalT &data, const Image3DType::Pointer &cpp_image) {

  G4AutoLock mutex(&SetPixelFluenceMutex);
  itk::ImageRegionIterator<Image3DType> iterator3D(
      cpp_image, cpp_image->GetLargestPossibleRegion());
  for (iterator3D.GoToBegin(); !iterator3D.IsAtEnd(); ++iterator3D) {
    Image3DType::IndexType index_f = iterator3D.GetIndex();
    Image3DType::PixelType pixelValue3D =
        data.squared_worker_flatimg[sub2ind(index_f)];
    ImageAddValue<Image3DType>(cpp_image, index_f, pixelValue3D * pixelValue3D);
  }
  // reset thread local data to zero
  const auto N_voxels = size_region[0] * size_region[1] * size_region[2];
  PrepareLocalDataForRun(data, N_voxels);
}

void GateFluenceActor::ScoreSquaredValue(threadLocalT &data,
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
      G4AutoLock mutex(&SetPixelFluenceMutex);
      ImageAddValue<Image3DType>(cpp_image, index, v * v); // implicit flush
    }
    // new temp value
    data.squared_worker_flatimg[index_flat] = value;
  }
}

void GateFluenceActor::PrepareLocalDataForRun(
    threadLocalT &data, const unsigned int numberOfVoxels) {
  data.squared_worker_flatimg.resize(numberOfVoxels);
  std::fill(data.squared_worker_flatimg.begin(),
            data.squared_worker_flatimg.end(), 0.0);
  data.lastid_worker_flatimg.resize(numberOfVoxels);
  std::fill(data.lastid_worker_flatimg.begin(),
            data.lastid_worker_flatimg.end(), 0);
}

void GateFluenceActor::InitializeUserInfo(py::dict &user_info) {
  // IMPORTANT: call the base class method
  GateVActor::InitializeUserInfo(user_info);
  fTranslation = DictGetG4ThreeVector(user_info, "translation");
  fSecondaries = DictGetBool(user_info,"images_for_scattering_processes");
}

void GateFluenceActor::InitializeCpp() {
  GateVActor::InitializeCpp();

  // Create the image pointer
  // (the size and allocation will be performed on the py side)
  cpp_counts_image = Image3DType::New();
  if (fSecondaries){
    cpp_counts_rayleigh_image = Image3DType::New();
    cpp_counts_compton_image = Image3DType::New();
    cpp_counts_secondaries_image =  Image3DType::New();
    cpp_counts_primaries_image =  Image3DType::New();
  }
  if (fCountsSquaredFlag) {
    cpp_counts_squared_image = Image3DType::New();
    if (fSecondaries){
      cpp_counts_squared_rayleigh_image = Image3DType::New();
      cpp_counts_squared_compton_image = Image3DType::New();
      cpp_counts_squared_secondaries_image =  Image3DType::New();
      cpp_counts_squared_primaries_image =  Image3DType::New();
    }
  }
  if (fEnergyFlag) {
    cpp_energy_image = Image3DType::New();
    if (fSecondaries){
      cpp_energy_rayleigh_image = Image3DType::New();
      cpp_energy_compton_image = Image3DType::New();
      cpp_energy_secondaries_image =  Image3DType::New();
      cpp_energy_primaries_image =  Image3DType::New();
    }
  }
  if (fEnergySquaredFlag) {
    cpp_energy_squared_image = Image3DType::New();
    if (fSecondaries){
      cpp_energy_squared_compton_image= Image3DType::New();
      cpp_energy_squared_rayleigh_image= Image3DType::New();
      cpp_energy_squared_secondaries_image= Image3DType::New();
      cpp_energy_squared_primaries_image=  Image3DType::New();
    }
  }
}

void GateFluenceActor::StartSimulationAction(){
  if (fSecondaries){
    auto* actorManager = GateActorManager::GetInstance();
    auto* actor = actorManager->GetActor(this->fActorName +"_processes");
    fLastProcessActor = dynamic_cast<GateDigiAttributeLastProcessDefinedStepInVolumeActor*>(actor);
  }


}

void GateFluenceActor::BeginOfEventAction(const G4Event *event) {
  G4AutoLock mutex(&SetNbEventMutexFluence);
  NbOfEvent++;
}

void GateFluenceActor::BeginOfRunAction(const G4Run *run) {
  const auto N_voxels = size_region[0] * size_region[1] * size_region[2];
  if (fEnergySquaredFlag) {
    PrepareLocalDataForRun(fThreadLocalDataEnergy.Get(), N_voxels);
    if (fSecondaries){
      PrepareLocalDataForRun(fThreadLocalDataComptEnergy.Get(), N_voxels);
      PrepareLocalDataForRun(fThreadLocalDataRaylEnergy.Get(), N_voxels);    
      PrepareLocalDataForRun(fThreadLocalDataSecEnergy.Get(), N_voxels);    
      PrepareLocalDataForRun(fThreadLocalDataPrimEnergy.Get(), N_voxels);          

    }
  }
  if (fCountsSquaredFlag) {
    PrepareLocalDataForRun(fThreadLocalDataCounts.Get(), N_voxels);
    if (fSecondaries){
      PrepareLocalDataForRun(fThreadLocalDataComptCounts.Get(), N_voxels);
      PrepareLocalDataForRun(fThreadLocalDataRaylCounts.Get(), N_voxels);    
      PrepareLocalDataForRun(fThreadLocalDataSecCounts.Get(), N_voxels);    
      PrepareLocalDataForRun(fThreadLocalDataPrimCounts.Get(), N_voxels);          

    }
  }
}

void GateFluenceActor::BeginOfRunActionMasterThread(int run_id) {
  // Important ! The volume may have moved, so we (re-)attach each run
  AttachImageToVolume<Image3DType>(cpp_counts_image, fPhysicalVolumeName,
                                   fTranslation);
  if (fSecondaries){
    AttachImageToVolume<Image3DType>(cpp_counts_compton_image, fPhysicalVolumeName,
                                   fTranslation);
    AttachImageToVolume<Image3DType>(cpp_counts_rayleigh_image, fPhysicalVolumeName,
                                   fTranslation);
    AttachImageToVolume<Image3DType>(cpp_counts_secondaries_image, fPhysicalVolumeName,
                                   fTranslation);
    AttachImageToVolume<Image3DType>(cpp_counts_primaries_image, fPhysicalVolumeName,
                                   fTranslation);
  }
  if (fEnergyFlag) {
    AttachImageToVolume<Image3DType>(cpp_energy_image, fPhysicalVolumeName,
                                     fTranslation);
    if (fSecondaries){
      AttachImageToVolume<Image3DType>(cpp_energy_compton_image, fPhysicalVolumeName,
                                    fTranslation);
      AttachImageToVolume<Image3DType>(cpp_energy_rayleigh_image, fPhysicalVolumeName,
                                    fTranslation);
      AttachImageToVolume<Image3DType>(cpp_energy_secondaries_image, fPhysicalVolumeName,
                                    fTranslation);
      AttachImageToVolume<Image3DType>(cpp_energy_primaries_image, fPhysicalVolumeName,
                                    fTranslation);
  }
  }
  NbOfEvent = 0;
  Image3DType::RegionType region = cpp_counts_image->GetLargestPossibleRegion();
  size_region = region.GetSize();
}

void GateFluenceActor::SteppingAction(G4Step *step) {
  
  // same method to consider only entering tracks
  if (step->GetPreStepPoint()->GetStepStatus() == fGeomBoundary) {
    G4String lastProcessName;
    if (fSecondaries)
      lastProcessName = fLastProcessActor->GetLastProcess();
  
    // the pre-position is at the edge
    const auto event_id =
        G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
    auto preGlobal = step->GetPreStepPoint()->GetPosition();
    auto dir = step->GetPreStepPoint()->GetMomentumDirection();
    auto touchable = step->GetPreStepPoint()->GetTouchable();
    auto energy = step->GetPreStepPoint()->GetKineticEnergy();

    // consider position in the local volume, slightly shifted by 0.1 nm because
    // otherwise, it can be considered as outside the volume by isInside.
    auto position = preGlobal + 0.1 * CLHEP::nm * dir;
    auto localPosition =
        touchable->GetHistory()->GetTransform(0).TransformPoint(position);

    // convert G4ThreeVector to itk PointType
    Image3DType::PointType point;
    point[0] = localPosition[0];
    point[1] = localPosition[1];
    point[2] = localPosition[2];

    // get weight
    auto w = step->GetTrack()->GetWeight();

    // get pixel index
    Image3DType::IndexType index;
    bool isInside =
        cpp_counts_image->TransformPhysicalPointToIndex(point, index);

    // set value
    
    if (isInside) {
      G4String creatorProcessName = "None";
      if (step->GetTrack()->GetCreatorProcess() !=0 ){
        creatorProcessName = step->GetTrack()->GetCreatorProcess()->GetProcessName();
      }
      {
        G4AutoLock FluenceMutex(&SetPixelFluenceMutex);
        ImageAddValue<Image3DType>(cpp_counts_image, index, w);


        
        if (fSecondaries){

          if ((lastProcessName == "compt") || (creatorProcessName == "biasWrapper(compt)")){
            ImageAddValue<Image3DType>(cpp_counts_compton_image, index, w);
          }
          if ((lastProcessName == "Rayl") || (creatorProcessName == "biasWrapper(Rayl)")){
            ImageAddValue<Image3DType>(cpp_counts_rayleigh_image, index, w);
          }
          if (((lastProcessName == "Rayl") || (creatorProcessName == "biasWrapper(Rayl)")) || 
          ((lastProcessName == "compt") || (creatorProcessName == "biasWrapper(compt)"))){
            ImageAddValue<Image3DType>(cpp_counts_secondaries_image, index, w);
          }
          else{
            ImageAddValue<Image3DType>(cpp_counts_primaries_image, index, w);
          }
        }
        if (fEnergyFlag){
          ImageAddValue<Image3DType>(cpp_energy_image, index, energy * w);
          if (fSecondaries){
            if ((lastProcessName == "compt") || (creatorProcessName == "biasWrapper(compt)")){
              ImageAddValue<Image3DType>(cpp_energy_compton_image, index, energy * w);
            }
            if ((lastProcessName == "Rayl") || (creatorProcessName == "biasWrapper(Rayl)")){
              ImageAddValue<Image3DType>(cpp_energy_rayleigh_image, index, energy * w);
            }
            if (((lastProcessName == "Rayl") || (creatorProcessName == "biasWrapper(Rayl)")) || 
            ((lastProcessName == "compt") || (creatorProcessName == "biasWrapper(compt)"))){
              ImageAddValue<Image3DType>(cpp_energy_secondaries_image, index, energy * w);
            }
            else{
              ImageAddValue<Image3DType>(cpp_energy_primaries_image, index, energy * w);
            }
          }
      }
      }
      // else : outside the image

      if (fCountsSquaredFlag || fEnergySquaredFlag) {
        if (fEnergySquaredFlag) {
          ScoreSquaredValue(fThreadLocalDataEnergy.Get(),
                            cpp_energy_squared_image, energy * w, event_id,
                            index);
          if (fSecondaries){
            if ((lastProcessName == "compt") || (creatorProcessName == "biasWrapper(compt)")){
              ScoreSquaredValue(fThreadLocalDataComptEnergy.Get(),
                            cpp_energy_squared_compton_image, energy * w, event_id,
                            index);
            }
            if ((lastProcessName == "Rayl") || (creatorProcessName == "biasWrapper(Rayl)")){
              ScoreSquaredValue(fThreadLocalDataRaylEnergy.Get(),
                            cpp_energy_squared_rayleigh_image, energy * w, event_id,
                            index);
            }
            if (((lastProcessName == "Rayl") || (creatorProcessName == "biasWrapper(Rayl)")) || 
            ((lastProcessName == "compt") || (creatorProcessName == "biasWrapper(compt)"))){
              ScoreSquaredValue(fThreadLocalDataSecEnergy.Get(),
                            cpp_energy_squared_secondaries_image, energy * w, event_id,
                            index);
            }
            else{
              ScoreSquaredValue(fThreadLocalDataPrimEnergy.Get(),
                            cpp_energy_squared_primaries_image, energy * w, event_id,
                            index);
              
            }
          }
        }
        if (fCountsSquaredFlag) {
          ScoreSquaredValue(fThreadLocalDataCounts.Get(),
                            cpp_counts_squared_image, w, event_id, index);
          if (fSecondaries){
            if ((lastProcessName == "compt") || (creatorProcessName == "biasWrapper(compt)")){
              ScoreSquaredValue(fThreadLocalDataComptCounts.Get(),
                            cpp_counts_squared_compton_image, w, event_id,
                            index);
            }
            if ((lastProcessName == "Rayl") || (creatorProcessName == "biasWrapper(Rayl)")){
              ScoreSquaredValue(fThreadLocalDataRaylCounts.Get(),
                            cpp_counts_squared_rayleigh_image, w, event_id,
                            index);
            }
            if (((lastProcessName == "Rayl") || (creatorProcessName == "biasWrapper(Rayl)")) || 
            ((lastProcessName == "compt") || (creatorProcessName == "biasWrapper(compt)"))){
              ScoreSquaredValue(fThreadLocalDataSecCounts.Get(),
                            cpp_counts_squared_secondaries_image, w, event_id,
                            index);
            }
            else{
              
              ScoreSquaredValue(fThreadLocalDataPrimCounts.Get(),
                            cpp_counts_squared_primaries_image, w, event_id,
                            index);
            }

          }
        }
      }
    }
  }
}

void GateFluenceActor::EndOfEventAction(const G4Event *event) {
  if (fCountsSquaredFlag) {
    FlushSquaredValues(fThreadLocalDataCounts.Get(), cpp_counts_squared_image);
    if (fSecondaries){
          FlushSquaredValues(fThreadLocalDataComptCounts.Get(), cpp_counts_squared_compton_image);
          FlushSquaredValues(fThreadLocalDataRaylCounts.Get(), cpp_counts_squared_rayleigh_image);
          FlushSquaredValues(fThreadLocalDataSecCounts.Get(), cpp_counts_squared_secondaries_image);
          FlushSquaredValues(fThreadLocalDataPrimCounts.Get(), cpp_counts_squared_primaries_image);
      }
  

  }
  if (fEnergySquaredFlag) {
    FlushSquaredValues(fThreadLocalDataEnergy.Get(), cpp_energy_squared_image);
    if (fSecondaries){
        FlushSquaredValues(fThreadLocalDataComptEnergy.Get(), cpp_energy_squared_compton_image);
        FlushSquaredValues(fThreadLocalDataRaylEnergy.Get(), cpp_energy_squared_rayleigh_image);
        FlushSquaredValues(fThreadLocalDataSecEnergy.Get(), cpp_energy_squared_secondaries_image);
        FlushSquaredValues(fThreadLocalDataPrimEnergy.Get(), cpp_energy_squared_primaries_image);
    }
  }
}
