/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerProjectionActor.h"
#include "../GateHelpersDict.h"
#include "../GateHelpersImage.h"
#include "G4RunManager.hh"
#include "GateDigiCollectionManager.h"
#include <iostream>

G4Mutex DigitizerProjectionActorMutex = G4MUTEX_INITIALIZER;

GateDigitizerProjectionActor::GateDigitizerProjectionActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  fActions.insert("StartSimulationAction");
  fActions.insert("EndOfEventAction");
  fActions.insert("BeginOfRunAction");
  fOutputFilename = DictGetStr(user_info, "output");
  auto r = DictGetMatrix(user_info, "detector_orientation_matrix");
  fDetectorOrientationMatrix = ConvertToG4RotationMatrix(r);
  fInputDigiCollectionNames =
      DictGetVecStr(user_info, "input_digi_collections");
  fImage = ImageType::New();
}

GateDigitizerProjectionActor::~GateDigitizerProjectionActor() = default;

// Called when the simulation start
void GateDigitizerProjectionActor::StartSimulationAction() {
  // Get input hits collection
  auto *hcm = GateDigiCollectionManager::GetInstance();
  for (const auto &name : fInputDigiCollectionNames) {
    auto *hc = hcm->GetDigiCollection(name);
    fInputDigiCollections.push_back(hc);
    CheckRequiredAttribute(hc, "PostPosition");
  }
}

void GateDigitizerProjectionActor::BeginOfRunAction(const G4Run *run) {
  auto &l = fThreadLocalData.Get();
  if (run->GetRunID() == 0) {
    // The first time here we need to initialize the input position
    l.fInputPos.resize(fInputDigiCollectionNames.size());
    for (size_t slice = 0; slice < fInputDigiCollections.size(); slice++) {
      auto *att_pos =
          fInputDigiCollections[slice]->GetDigiAttribute("PostPosition");
      l.fInputPos[slice] = &att_pos->Get3Values();
    }
  }

  // Important ! The volume may have moved, so we re-attach each run
  G4AutoLock mutex(&DigitizerProjectionActorMutex);
  AttachImageToVolume<ImageType>(fImage, fPhysicalVolumeName, G4ThreeVector(),
                                 fDetectorOrientationMatrix);
}

void GateDigitizerProjectionActor::EndOfEventAction(const G4Event * /*event*/) {
  G4AutoLock mutex(&DigitizerProjectionActorMutex);
  auto run = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
  for (size_t channel = 0; channel < fInputDigiCollections.size(); channel++) {
    auto slice = channel + run * fInputDigiCollections.size();
    ProcessSlice(slice, channel);
  }
}

void GateDigitizerProjectionActor::ProcessSlice(long slice, size_t channel) {
  auto &l = fThreadLocalData.Get();
  auto *hc = fInputDigiCollections[channel];
  auto index = hc->GetBeginOfEventIndex();
  auto n = hc->GetSize() - index;
  // If no new hits, do nothing
  if (n <= 0)
    return;

  // FIXME store other attributes somewhere ?
  const auto &pos = *l.fInputPos[channel];
  ImageType::PointType point;
  ImageType::IndexType pindex;

  // loop on channels
  for (size_t i = index; i < hc->GetSize(); i++) {
    // get position from input collection
    for (auto j = 0; j < 3; j++)
      point[j] = pos[i][j];

    bool isInside = fImage->TransformPhysicalPointToIndex(point, pindex);
    if (isInside) {
      // force the slice according to the channel
      pindex[2] = slice;
      ImageAddValue<ImageType>(fImage, pindex, 1);
    } else {
      // Should never be here (?)
      /*DDDV(pos);
      DDE(point);
      DDE(isInside);
      DDE(pindex);
      DDE(slice);
      DDE(fImage->GetLargestPossibleRegion().GetSize());
      nout++;
      DDE(nout);*/
    }
  }
}
