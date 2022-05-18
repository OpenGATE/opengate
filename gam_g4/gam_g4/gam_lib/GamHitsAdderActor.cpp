/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <iostream>
#include "GamHitsAdderActor.h"
#include "GamHelpersDict.h"
#include "GamHitsCollectionManager.h"
#include "GamHitsAdderInVolume.h"

GamHitsAdderActor::GamHitsAdderActor(py::dict &user_info)
        : GamVActor(user_info) {
    fActions.insert("StartSimulationAction");
    fActions.insert("EndOfEventAction");
    fActions.insert("BeginOfRunAction");
    fActions.insert("EndOfRunAction");
    fActions.insert("EndOfSimulationWorkerAction");
    fActions.insert("EndSimulationAction");
    fOutputFilename = DictGetStr(user_info, "output");
    fOutputHitsCollectionName = DictGetStr(user_info, "name");
    fInputHitsCollectionName = DictGetStr(user_info, "input_hits_collection");
    fUserSkipHitAttributeNames = DictGetVecStr(user_info, "skip_attributes");

    fPolicy = AdderPolicy::Error;
    auto policy = DictGetStr(user_info, "policy");
    if (policy == "EnergyWinnerPosition") fPolicy = AdderPolicy::EnergyWinnerPosition;
    else if (policy == "EnergyWeightedCentroidPosition") fPolicy = AdderPolicy::EnergyWeightedCentroidPosition;
    if (fPolicy == AdderPolicy::Error) {
        std::ostringstream oss;
        oss
                << "Error in GamHitsAdderActor: unknown policy. Must be EnergyWinnerPosition or EnergyWeightedCentroidPosition"
                << " while '" << policy << "' is read.";
        Fatal(oss.str());
    }
    fOutputHitsCollection = nullptr;
    fInputHitsCollection = nullptr;
}

GamHitsAdderActor::~GamHitsAdderActor() = default;

// Called when the simulation start
void GamHitsAdderActor::StartSimulationAction() {
    //Get the input hits collection
    auto *hcm = GamHitsCollectionManager::GetInstance();
    fInputHitsCollection = hcm->GetHitsCollection(fInputHitsCollectionName);
    CheckRequiredAttribute(fInputHitsCollection, "TotalEnergyDeposit");
    CheckRequiredAttribute(fInputHitsCollection, "PostPosition");
    CheckRequiredAttribute(fInputHitsCollection, "PostStepUniqueVolumeID");
    CheckRequiredAttribute(fInputHitsCollection, "GlobalTime");

    // Create the list of output attributes
    auto names = fInputHitsCollection->GetHitAttributeNames();
    for (const auto &n: fUserSkipHitAttributeNames) {
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
void GamHitsAdderActor::BeginOfRunAction(const G4Run *run) {
    if (run->GetRunID() == 0)
        InitializeComputation();
}

void GamHitsAdderActor::InitializeComputation() {
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
    l.fHitsAttributeFiller = new GamHitsAttributesFiller(fInputHitsCollection,
                                                         fOutputHitsCollection, names);

    // set output pointers to the attributes needed for computation
    l.fOutputEdepAttribute = fOutputHitsCollection->GetHitAttribute("TotalEnergyDeposit");
    l.fOutputPosAttribute = fOutputHitsCollection->GetHitAttribute("PostPosition");
    l.fOutputGlobalTimeAttribute = fOutputHitsCollection->GetHitAttribute("GlobalTime");

    // set input pointers to the attributes needed for computation
    l.fInputIter = fInputHitsCollection->NewIterator();
    l.fInputIter.TrackAttribute("TotalEnergyDeposit", &l.edep);
    l.fInputIter.TrackAttribute("PostPosition", &l.pos);
    l.fInputIter.TrackAttribute("PostStepUniqueVolumeID", &l.volID);
    l.fInputIter.TrackAttribute("GlobalTime", &l.time);
}

void GamHitsAdderActor::EndOfEventAction(const G4Event */*unused*/) {
    // loop on all hits to group per volume ID
    auto &l = fThreadLocalData.Get();
    auto &iter = l.fInputIter;
    iter.GoToBegin();
    while (!iter.IsAtEnd()) {
        AddHitPerVolume();
        iter++;
    }

    // create the output hits collection for grouped hits
    for (auto &h: l.fMapOfHitsInVolume) {
        auto &hit = h.second;
        // terminate the merge
        hit.Terminate(fPolicy);
        // Don't store if edep is zero
        if (hit.fFinalEdep > 0) {
            // (all "Fill" calls are thread local)
            l.fOutputEdepAttribute->FillDValue(hit.fFinalEdep);
            l.fOutputPosAttribute->Fill3Value(hit.fFinalPosition);
            l.fOutputGlobalTimeAttribute->FillDValue(hit.fFinalTime);
            l.fHitsAttributeFiller->Fill(hit.fFinalIndex);
        }
    }

    // reset the structure of hits
    l.fMapOfHitsInVolume.clear();
}

void GamHitsAdderActor::AddHitPerVolume() {
    auto &l = fThreadLocalData.Get();
    auto i = l.fInputIter.fIndex;
    if (*l.edep == 0) return;
    if (l.fMapOfHitsInVolume.count(*l.volID) == 0) {
        l.fMapOfHitsInVolume[*l.volID] = GamHitsAdderInVolume();
    }
    l.fMapOfHitsInVolume[*l.volID].Update(fPolicy, i, *l.edep, *l.pos, *l.time);
}

// Called every time a Run ends
void GamHitsAdderActor::EndOfRunAction(const G4Run * /*unused*/) {
    fOutputHitsCollection->FillToRoot();
    auto &iter = fThreadLocalData.Get().fInputIter;
    iter.Reset();
}

// Called every time a Run ends
void GamHitsAdderActor::EndOfSimulationWorkerAction(const G4Run * /*unused*/) {
    fOutputHitsCollection->Write();
}

// Called when the simulation end
void GamHitsAdderActor::EndSimulationAction() {
    fOutputHitsCollection->Write();
    fOutputHitsCollection->Close();
}

