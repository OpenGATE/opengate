/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerEnergyWindowsActor.h"
#include "../GateHelpersDict.h"
#include "GateDigiCollectionManager.h"
#include <iostream>

GateDigitizerEnergyWindowsActor::GateDigitizerEnergyWindowsActor(
    py::dict &user_info)
    : GateVActor(user_info, true) {
  // actions
  fActions.insert("StartSimulationAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("EndOfEventAction");
  fActions.insert("EndOfRunAction");
  fActions.insert("EndOfSimulationWorkerAction");
  fActions.insert("EndSimulationAction");
}

void GateDigitizerEnergyWindowsActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  // options
  fInputDigiCollectionName = DictGetStr(user_info, "input_digi_collection");
  fUserSkipDigiAttributeNames = DictGetVecStr(user_info, "skip_attributes");
  fClearEveryNEvents = DictGetInt(user_info, "clear_every");

  // Get information for all channels
  const auto dv = DictGetVecDict(user_info, "channels");
  for (auto d : dv) {
    fChannelNames.push_back(DictGetStr(d, "name"));
    fChannelMin.push_back(DictGetDouble(d, "min"));
    fChannelMax.push_back(DictGetDouble(d, "max"));
  }
}

void GateDigitizerEnergyWindowsActor::InitializeCpp() {
  GateVActor::InitializeCpp();
  fInputDigiCollection = nullptr;
}

// Called when the simulation starts
void GateDigitizerEnergyWindowsActor::StartSimulationAction() {
  // Get input digi collection
  auto *hcm = GateDigiCollectionManager::GetInstance();
  fInputDigiCollection = hcm->GetDigiCollection(fInputDigiCollectionName);
  CheckRequiredAttribute(fInputDigiCollection, "TotalEnergyDeposit");
  // Create the list of output attributes
  auto names = fInputDigiCollection->GetDigiAttributeNames();
  for (const auto &n : fUserSkipDigiAttributeNames) {
    if (names.count(n) > 0)
      names.erase(n);
  }
  // Create the output digi collections (one for each energy window channel)
  for (const auto &name : fChannelNames) {
    auto *hc = hcm->NewDigiCollection(name);
    std::string outputPath;
    if (!GetWriteToDisk(fOutputNameRoot)) {
      outputPath = "";
    } else {
      outputPath = GetOutputPath(fOutputNameRoot);
    }
    hc->SetFilenameAndInitRoot(outputPath);
    // hc->InitDigiAttributesFromNames(names);
    hc->InitDigiAttributesFromCopy(fInputDigiCollection,
                                   fUserSkipDigiAttributeNames);
    hc->RootInitializeTupleForMaster();
    fChannelDigiCollections.push_back(hc);
  }
}

void GateDigitizerEnergyWindowsActor::BeginOfRunAction(const G4Run *run) {
  auto &l = fThreadLocalData.Get();
  if (run->GetRunID() == 0) {
    // Create the output digi collections (one for each energy window channel)
    for (auto *hc : fChannelDigiCollections) {
      // Init a Filler of all others attributes (all except edep and pos)
      auto *f = new GateDigiAttributesFiller(fInputDigiCollection, hc,
                                             hc->GetDigiAttributeNames());
      l.fFillers.push_back(f);
    }
    for (auto *hc : fChannelDigiCollections) {
      hc->RootInitializeTupleForWorker();
    }
    l.fInputEdep = &fInputDigiCollection->GetDigiAttribute("TotalEnergyDeposit")
                        ->GetDValues();
  }
}

void GateDigitizerEnergyWindowsActor::BeginOfEventAction(const G4Event *event) {
  const bool must_clear = event->GetEventID() % fClearEveryNEvents == 0;
  for (auto *hc : fChannelDigiCollections) {
    hc->FillToRootIfNeeded(must_clear);
  }
  fThreadLocalData.Get().fLastEnergyWindowId = -1;
}

void GateDigitizerEnergyWindowsActor::EndOfEventAction(
    const G4Event * /*event*/) {
  const auto index = fInputDigiCollection->GetBeginOfEventIndex();
  auto n = fInputDigiCollection->GetSize() - index;
  // If no new hits, do nothing
  if (n <= 0)
    return;
  // init last energy windows to 'outside' (-1)
  for (size_t i = 0; i < fChannelDigiCollections.size(); i++) {
    ApplyThreshold(i, fChannelMin[i], fChannelMax[i]);
  }
}

void GateDigitizerEnergyWindowsActor::ApplyThreshold(const size_t i,
                                                     const double min,
                                                     const double max) const {
  auto &l = fThreadLocalData.Get();
  // get the vector of values
  const auto &edep = *l.fInputEdep;
  // get the index of the first hit for this event
  const auto index = fInputDigiCollection->GetBeginOfEventIndex();
  // fill all the hits
  for (size_t n = index; n < fInputDigiCollection->GetSize(); n++) {
    auto e = edep[n];
    if (e >= min && e < max) { // FIXME put in doc. strictly or not ?
      l.fFillers[i]->Fill(n);
      l.fLastEnergyWindowId = i;
    }
  }
}

int GateDigitizerEnergyWindowsActor::GetLastEnergyWindowId() const {
  return fThreadLocalData.Get().fLastEnergyWindowId;
}

// Called every time a Run ends
void GateDigitizerEnergyWindowsActor::EndOfRunAction(const G4Run * /*run*/) {
  for (auto *hc : fChannelDigiCollections)
    hc->FillToRootIfNeeded(true);
}

// Called every time a Run ends
void GateDigitizerEnergyWindowsActor::EndOfSimulationWorkerAction(
    const G4Run * /*run*/) {
  for (const auto *hc : fChannelDigiCollections)
    hc->Write();
}

// Called when the simulation ends
void GateDigitizerEnergyWindowsActor::EndSimulationAction() {
  for (const auto *hc : fChannelDigiCollections) {
    hc->Write();
    hc->Close();
  }
}
