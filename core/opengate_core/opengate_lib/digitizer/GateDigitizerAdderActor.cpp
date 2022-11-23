/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerAdderActor.h"
#include "../GateHelpersDict.h"
#include "GateDigiAdderInVolume.h"
#include "GateDigiCollectionManager.h"
#include <iostream>

GateDigitizerAdderActor::GateDigitizerAdderActor(py::dict &user_info)
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
    oss << "Error in GateDigitizerAdderActor: unknown policy. Must be "
           "EnergyWinnerPosition or EnergyWeightedCentroidPosition"
        << " while '" << policy << "' is read.";
    Fatal(oss.str());
  }

  // init
  fOutputHitsCollection = nullptr;
  fInputHitsCollection = nullptr;
  fGroupVolumeDepth = -1;
}

GateDigitizerAdderActor::~GateDigitizerAdderActor() = default;

void GateDigitizerAdderActor::SetGroupVolumeDepth(int depth) {
  fGroupVolumeDepth = depth;
}

void GateDigitizerAdderActor::StartSimulationAction() {
  // Get the input hits collection
  auto *hcm = GateDigiCollectionManager::GetInstance();
  fInputHitsCollection = hcm->GetDigiCollection(fInputHitsCollectionName);
  CheckRequiredAttribute(fInputHitsCollection, "TotalEnergyDeposit");
  CheckRequiredAttribute(fInputHitsCollection, "PostPosition");
  CheckRequiredAttribute(fInputHitsCollection, "PreStepUniqueVolumeID");
  CheckRequiredAttribute(fInputHitsCollection, "GlobalTime");

  // Create the list of output attributes
  auto names = fInputHitsCollection->GetDigiAttributeNames();
  for (const auto &n : fUserSkipHitAttributeNames) {
    if (names.count(n) > 0)
      names.erase(n);
  }

  // Create the output hits collection with the same list of attributes
  fOutputHitsCollection = hcm->NewDigiCollection(fOutputHitsCollectionName);
  fOutputHitsCollection->SetFilename(fOutputFilename);
  fOutputHitsCollection->InitializeDigiAttributes(names);
  fOutputHitsCollection->InitializeRootTupleForMaster();
}

void GateDigitizerAdderActor::BeginOfRunAction(const G4Run *run) {
  if (run->GetRunID() == 0)
    InitializeComputation();
}

void GateDigitizerAdderActor::InitializeComputation() {
  fOutputHitsCollection->InitializeRootTupleForWorker();

  // Init a Filler of all attributes except edep,
  // pos and time that will be set explicitly
  auto names = fOutputHitsCollection->GetDigiAttributeNames();
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
      fOutputHitsCollection->GetDigiAttribute("TotalEnergyDeposit");
  fOutputPosAttribute = fOutputHitsCollection->GetDigiAttribute("PostPosition");
  fOutputGlobalTimeAttribute =
      fOutputHitsCollection->GetDigiAttribute("GlobalTime");

  // set input pointers to the attributes needed for computation
  l.fInputIter = fInputHitsCollection->NewIterator();
  l.fInputIter.TrackAttribute("TotalEnergyDeposit", &l.edep);
  l.fInputIter.TrackAttribute("PostPosition", &l.pos);
  l.fInputIter.TrackAttribute("PreStepUniqueVolumeID", &l.volID);
  l.fInputIter.TrackAttribute("GlobalTime", &l.time);
}

void GateDigitizerAdderActor::BeginOfEventAction(const G4Event *event) {
  bool must_clear = event->GetEventID() % fClearEveryNEvents == 0;
  fOutputHitsCollection->FillToRootIfNeeded(must_clear);
}

void GateDigitizerAdderActor::EndOfEventAction(const G4Event * /*unused*/) {
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

void GateDigitizerAdderActor::AddHitPerVolume() {
  auto &l = fThreadLocalData.Get();
  auto i = l.fInputIter.fIndex;
  if (*l.edep == 0)
    return;
  auto uid = l.volID->get()->GetIdUpToDepth(fGroupVolumeDepth);
  if (l.fMapOfHitsInVolume.count(uid) == 0) {
    l.fMapOfHitsInVolume[uid] = GateDigiAdderInVolume();
  }
  l.fMapOfHitsInVolume[uid].Update(fPolicy, i, *l.edep, *l.pos, *l.time);
}

// Called every time a Run ends
void GateDigitizerAdderActor::EndOfRunAction(const G4Run * /*unused*/) {
  fOutputHitsCollection->FillToRootIfNeeded(true);
  auto &iter = fThreadLocalData.Get().fInputIter;
  iter.Reset();
}

// Called every time a Run ends
void GateDigitizerAdderActor::EndOfSimulationWorkerAction(
    const G4Run * /*unused*/) {
  fOutputHitsCollection->Write();
}

// Called when the simulation end
void GateDigitizerAdderActor::EndSimulationAction() {
  fOutputHitsCollection->Write();
  fOutputHitsCollection->Close();
}
