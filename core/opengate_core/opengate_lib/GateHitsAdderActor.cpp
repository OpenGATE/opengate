/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHitsAdderActor.h"
#include "GateHelpersDict.h"
#include "GateHitsAdderInVolume.h"
#include "GateHitsCollectionManager.h"
#include <iostream>

GateHitsAdderActor::GateHitsAdderActor(py::dict &user_info)
    : GateVActor(user_info, true) {
  // actions
  fActions.insert("StartSimulationAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("EndOfEventAction");
  fActions.insert("EndOfRunAction");
  fActions.insert("EndOfSimulationWorkerAction");
  fActions.insert("EndSimulationAction");
  // options
  fOutputFilename = DictGetStr(user_info, "output");
  fOutputHitsCollectionName = DictGetStr(user_info, "_name");
  fInputHitsCollectionName = DictGetStr(user_info, "input_hits_collection");
  fUserSkipHitAttributeNames = DictGetVecStr(user_info, "skip_attributes");
  fClearEveryNEvents = DictGetInt(user_info, "clear_every");
  // policy
  fPolicy = AdderPolicy::Error;
  auto policy = DictGetStr(user_info, "policy");
  if (policy == "EnergyWinnerPosition")
    fPolicy = AdderPolicy::EnergyWinnerPosition;
  else if (policy == "EnergyWeightedCentroidPosition")
    fPolicy = AdderPolicy::EnergyWeightedCentroidPosition;
  if (fPolicy == AdderPolicy::Error) {
    std::ostringstream oss;
    oss << "Error in GateHitsAdderActor: unknown policy. Must be "
           "EnergyWinnerPosition or EnergyWeightedCentroidPosition"
        << " while '" << policy << "' is read.";
    Fatal(oss.str());
  }
  // init
  fOutputHitsCollection = nullptr;
  fInputHitsCollection = nullptr;
}

GateHitsAdderActor::~GateHitsAdderActor() = default;

// Called when the simulation start
void GateHitsAdderActor::StartSimulationAction() {
  // Get the input hits collection
  auto *hcm = GateHitsCollectionManager::GetInstance();
  fInputHitsCollection = hcm->GetHitsCollection(fInputHitsCollectionName);
  CheckRequiredAttribute(fInputHitsCollection, "TotalEnergyDeposit");
  CheckRequiredAttribute(fInputHitsCollection, "PostPosition");
  CheckRequiredAttribute(fInputHitsCollection, "PostStepUniqueVolumeID");
  CheckRequiredAttribute(fInputHitsCollection, "GlobalTime");

  // Create the list of output attributes
  auto names = fInputHitsCollection->GetHitAttributeNames();
  for (const auto &n : fUserSkipHitAttributeNames) {
    if (names.count(n) > 0)
      names.erase(n);
  }

  // Create the output hits collection with the same list of attributes
  fOutputHitsCollection = hcm->NewHitsCollection(fOutputHitsCollectionName);
  fOutputHitsCollection->SetFilename(fOutputFilename);
  fOutputHitsCollection->InitializeHitAttributes(names);
  fOutputHitsCollection->InitializeRootTupleForMaster();
}

// Called every time a Run starts
void GateHitsAdderActor::BeginOfRunAction(const G4Run *run) {
  if (run->GetRunID() == 0)
    InitializeComputation();
}

void GateHitsAdderActor::InitializeComputation() {
  fOutputHitsCollection->InitializeRootTupleForWorker();

  // Init a Filler of all attributes except edep,
  // pos and time that will be set explicitly
  auto names = fOutputHitsCollection->GetHitAttributeNames();
  names.erase("TotalEnergyDeposit");
  names.erase("PostPosition");
  names.erase("GlobalTime");

  // Get thread local variables
  auto &l = fThreadLocalData.Get();

  // Create Filler of all remaining attributes (except the required ones)
  l.fHitsAttributeFiller = new GateHitsAttributesFiller(
      fInputHitsCollection, fOutputHitsCollection, names);

  // set output pointers to the attributes needed for computation
  fOutputEdepAttribute =
      fOutputHitsCollection->GetHitAttribute("TotalEnergyDeposit");
  fOutputPosAttribute = fOutputHitsCollection->GetHitAttribute("PostPosition");
  fOutputGlobalTimeAttribute =
      fOutputHitsCollection->GetHitAttribute("GlobalTime");

  // set input pointers to the attributes needed for computation
  l.fInputIter = fInputHitsCollection->NewIterator();
  l.fInputIter.TrackAttribute("TotalEnergyDeposit", &l.edep);
  l.fInputIter.TrackAttribute("PostPosition", &l.pos);
  // Should probably be PreStep instead of PostStep here
  // However, it was Pre in Gate legacy, and does not change because when a step
  // terminate at the end of a volume, this is 'transportation' with edep==0, so
  // ignored
  l.fInputIter.TrackAttribute("PostStepUniqueVolumeID", &l.volID);
  l.fInputIter.TrackAttribute("GlobalTime", &l.time);
}

void GateHitsAdderActor::BeginOfEventAction(const G4Event *event) {
  bool must_clear = event->GetEventID() % fClearEveryNEvents == 0;
  fOutputHitsCollection->FillToRootIfNeeded(must_clear);
}

void GateHitsAdderActor::EndOfEventAction(const G4Event * /*unused*/) {
  // loop on all hits to group per volume ID
  auto &l = fThreadLocalData.Get();
  auto &iter = l.fInputIter;
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    AddHitPerVolume();
    iter++;
  }

  // create the output hits collection for grouped hits
  for (auto &h : l.fMapOfHitsInVolume) {
    auto &hit = h.second;
    // terminate the merge
    hit.Terminate(fPolicy);
    // Don't store if edep is zero
    if (hit.fFinalEdep > 0) {
      // (all "Fill" calls are thread local)
      fOutputEdepAttribute->FillDValue(hit.fFinalEdep);
      fOutputPosAttribute->Fill3Value(hit.fFinalPosition);
      fOutputGlobalTimeAttribute->FillDValue(hit.fFinalTime);
      l.fHitsAttributeFiller->Fill(hit.fFinalIndex);
    }
  }

  // reset the structure of hits
  l.fMapOfHitsInVolume.clear();
}

void GateHitsAdderActor::AddHitPerVolume() {
  auto &l = fThreadLocalData.Get();
  auto i = l.fInputIter.fIndex;
  if (*l.edep == 0)
    return;
  if (l.fMapOfHitsInVolume.count(*l.volID) == 0) {
    l.fMapOfHitsInVolume[*l.volID] = GateHitsAdderInVolume();
  }
  l.fMapOfHitsInVolume[*l.volID].Update(fPolicy, i, *l.edep, *l.pos, *l.time);
}

// Called every time a Run ends
void GateHitsAdderActor::EndOfRunAction(const G4Run * /*unused*/) {
  fOutputHitsCollection->FillToRootIfNeeded(true);
  auto &iter = fThreadLocalData.Get().fInputIter;
  iter.Reset();
}

// Called every time a Run ends
void GateHitsAdderActor::EndOfSimulationWorkerAction(const G4Run * /*unused*/) {
  fOutputHitsCollection->Write();
}

// Called when the simulation end
void GateHitsAdderActor::EndSimulationAction() {
  fOutputHitsCollection->Write();
  fOutputHitsCollection->Close();
}
