/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHitsProjectionActor.h"
#include "G4PhysicalVolumeStore.hh"
#include "G4RunManager.hh"
#include "GateHelpersDict.h"
#include "GateHelpersImage.h"
#include "digitizer/GateDigiCollectionManager.h"
#include <iostream>

GateHitsProjectionActor::GateHitsProjectionActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  fActions.insert("StartSimulationAction");
  fActions.insert("EndOfEventAction");
  fActions.insert("BeginOfRunAction");
  fOutputFilename = DictGetStr(user_info, "output");
  // fVolumeName = DictGetStr(user_info, "mother");
  fInputHitsCollectionNames =
      DictGetVecStr(user_info, "input_hits_collections");
  fImage = ImageType::New();
}

GateHitsProjectionActor::~GateHitsProjectionActor() {}

// Called when the simulation start
void GateHitsProjectionActor::StartSimulationAction() {
  // Get input hits collection
  auto *hcm = GateDigiCollectionManager::GetInstance();
  for (const auto &name : fInputHitsCollectionNames) {
    auto *hc = hcm->GetDigiCollection(name);
    fInputHitsCollections.push_back(hc);
    CheckRequiredAttribute(hc, "PostPosition");
  }
}

void GateHitsProjectionActor::BeginOfRunAction(const G4Run *run) {
  auto &l = fThreadLocalData.Get();
  if (run->GetRunID() == 0) {
    // The first time here we need to initialize the input position
    l.fInputPos.resize(fInputHitsCollectionNames.size());
    for (size_t slice = 0; slice < fInputHitsCollections.size(); slice++) {
      auto *att_pos =
          fInputHitsCollections[slice]->GetDigiAttribute("PostPosition");
      l.fInputPos[slice] = &att_pos->Get3Values();
    }
  }

  // Important ! The volume may have moved, so we re-attach each run
  AttachImageToVolume<ImageType>(fImage, fPhysicalVolumeName);
}

void GateHitsProjectionActor::EndOfEventAction(const G4Event * /*event*/) {
  auto run = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
  for (size_t channel = 0; channel < fInputHitsCollections.size(); channel++) {
    auto slice = channel + run * fInputHitsCollections.size();
    ProcessSlice(slice, channel);
  }
}

void GateHitsProjectionActor::ProcessSlice(long slice, size_t channel) {
  auto &l = fThreadLocalData.Get();
  auto *hc = fInputHitsCollections[channel];
  auto index = hc->GetBeginOfEventIndex();
  auto n = hc->GetSize() - index;
  // If no new hits, do nothing
  if (n <= 0)
    return;

  // FIXME store other attributes somewhere ?
  const auto &pos = *l.fInputPos[channel];
  ImageType::PointType point;
  ImageType::IndexType pindex;
  for (size_t i = index; i < hc->GetSize(); i++) {
    // get position from input collection
    for (auto j = 0; j < 3; j++)
      point[j] = pos[i][j];
    bool isInside = fImage->TransformPhysicalPointToIndex(point, pindex);
    // force the slice according to the channel
    pindex[2] = slice;
    if (isInside) {
      ImageAddValue<ImageType>(fImage, pindex, 1);
    } else {
      // Should never be here (?)
      /*
       DDD(isInside);
       DDD(pindex);
       DDD(fImage->GetLargestPossibleRegion().GetSize());
       */
    }
  }
}
