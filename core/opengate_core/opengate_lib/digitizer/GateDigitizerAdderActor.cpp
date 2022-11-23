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
  fOutputDigiCollectionName = DictGetStr(user_info, "_name");
  fInputDigiCollectionName = DictGetStr(user_info, "input_digi_collection");
  fUserSkipDigiAttributeNames = DictGetVecStr(user_info, "skip_attributes");
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
  fOutputDigiCollection = nullptr;
  fInputDigiCollection = nullptr;
  fGroupVolumeDepth = -1;
}

GateDigitizerAdderActor::~GateDigitizerAdderActor() = default;

void GateDigitizerAdderActor::SetGroupVolumeDepth(int depth) {
  fGroupVolumeDepth = depth;
}

void GateDigitizerAdderActor::StartSimulationAction() {
  // Get the input hits collection
  auto *hcm = GateDigiCollectionManager::GetInstance();
  fInputDigiCollection = hcm->GetDigiCollection(fInputDigiCollectionName);
  CheckRequiredAttribute(fInputDigiCollection, "TotalEnergyDeposit");
  CheckRequiredAttribute(fInputDigiCollection, "PostPosition");
  CheckRequiredAttribute(fInputDigiCollection, "PreStepUniqueVolumeID");
  CheckRequiredAttribute(fInputDigiCollection, "GlobalTime");

  // Create the list of output attributes
  auto names = fInputDigiCollection->GetDigiAttributeNames();
  for (const auto &n : fUserSkipDigiAttributeNames) {
    if (names.count(n) > 0)
      names.erase(n);
  }

  // Create the output hits collection with the same list of attributes
  fOutputDigiCollection = hcm->NewDigiCollection(fOutputDigiCollectionName);
  fOutputDigiCollection->SetFilename(fOutputFilename);
  fOutputDigiCollection->InitializeDigiAttributes(names);
  fOutputDigiCollection->InitializeRootTupleForMaster();
}

void GateDigitizerAdderActor::BeginOfRunAction(const G4Run *run) {
  if (run->GetRunID() == 0)
    InitializeComputation();
}

void GateDigitizerAdderActor::InitializeComputation() {
  fOutputDigiCollection->InitializeRootTupleForWorker();

  // Init a Filler of all attributes except edep,
  // pos and time that will be set explicitly
  auto names = fOutputDigiCollection->GetDigiAttributeNames();
  names.erase("TotalEnergyDeposit");
  names.erase("PostPosition");
  names.erase("GlobalTime");

  // Get thread local variables
  auto &l = fThreadLocalData.Get();

  // Create Filler of all remaining attributes (except the required ones)
  l.fDigiAttributeFiller = new GateDigiAttributesFiller(
      fInputDigiCollection, fOutputDigiCollection, names);

  // set output pointers to the attributes needed for computation
  fOutputEdepAttribute =
      fOutputDigiCollection->GetDigiAttribute("TotalEnergyDeposit");
  fOutputPosAttribute = fOutputDigiCollection->GetDigiAttribute("PostPosition");
  fOutputGlobalTimeAttribute =
      fOutputDigiCollection->GetDigiAttribute("GlobalTime");

  // set input pointers to the attributes needed for computation
  l.fInputIter = fInputDigiCollection->NewIterator();
  l.fInputIter.TrackAttribute("TotalEnergyDeposit", &l.edep);
  l.fInputIter.TrackAttribute("PostPosition", &l.pos);
  l.fInputIter.TrackAttribute("PreStepUniqueVolumeID", &l.volID);
  l.fInputIter.TrackAttribute("GlobalTime", &l.time);
}

void GateDigitizerAdderActor::BeginOfEventAction(const G4Event *event) {
  bool must_clear = event->GetEventID() % fClearEveryNEvents == 0;
  fOutputDigiCollection->FillToRootIfNeeded(must_clear);
}

void GateDigitizerAdderActor::EndOfEventAction(const G4Event * /*unused*/) {
  // loop on all hits to group per volume ID
  auto &l = fThreadLocalData.Get();
  auto &iter = l.fInputIter;
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    AddDigiPerVolume();
    iter++;
  }

  // create the output hits collection for grouped hits
  for (auto &h : l.fMapOfDigiInVolume) {
    auto &hit = h.second;
    // terminate the merge
    hit.Terminate(fPolicy);
    // Don't store if edep is zero
    if (hit.fFinalEdep > 0) {
      // (all "Fill" calls are thread local)
      fOutputEdepAttribute->FillDValue(hit.fFinalEdep);
      fOutputPosAttribute->Fill3Value(hit.fFinalPosition);
      fOutputGlobalTimeAttribute->FillDValue(hit.fFinalTime);
      l.fDigiAttributeFiller->Fill(hit.fFinalIndex);
    }
  }

  // reset the structure of hits
  l.fMapOfDigiInVolume.clear();
}

void GateDigitizerAdderActor::AddDigiPerVolume() {
  auto &l = fThreadLocalData.Get();
  auto i = l.fInputIter.fIndex;
  if (*l.edep == 0)
    return;
  auto uid = l.volID->get()->GetIdUpToDepth(fGroupVolumeDepth);
  if (l.fMapOfDigiInVolume.count(uid) == 0) {
    l.fMapOfDigiInVolume[uid] = GateDigiAdderInVolume();
  }
  l.fMapOfDigiInVolume[uid].Update(fPolicy, i, *l.edep, *l.pos, *l.time);
}

// Called every time a Run ends
void GateDigitizerAdderActor::EndOfRunAction(const G4Run * /*unused*/) {
  fOutputDigiCollection->FillToRootIfNeeded(true);
  auto &iter = fThreadLocalData.Get().fInputIter;
  iter.Reset();
}

// Called every time a Run ends
void GateDigitizerAdderActor::EndOfSimulationWorkerAction(
    const G4Run * /*unused*/) {
  fOutputDigiCollection->Write();
}

// Called when the simulation end
void GateDigitizerAdderActor::EndSimulationAction() {
  fOutputDigiCollection->Write();
  fOutputDigiCollection->Close();
}
