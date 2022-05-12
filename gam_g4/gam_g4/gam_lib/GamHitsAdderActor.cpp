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
#include "GamUniqueVolumeIDManager.h"

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

    // FIXME
    fEdepMin = 0 * CLHEP::eV;
    fEdepMax = 5150000 * CLHEP::keV;

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
    fThreadLocalData.Get().fIndex = 0;
}

GamHitsAdderActor::~GamHitsAdderActor() = default;

// Called when the simulation start
void GamHitsAdderActor::StartSimulationAction() {
    //Get the input hits collection
    auto *hcm = GamHitsCollectionManager::GetInstance();
    fInputHitsCollection = hcm->GetHitsCollection(fInputHitsCollectionName);
    CheckRequiredAttribute(fInputHitsCollection, "TotalEnergyDeposit");
    CheckRequiredAttribute(fInputHitsCollection, "PostPosition");
    CheckRequiredAttribute(fInputHitsCollection, "PreStepUniqueVolumeID");
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
    // reset index (because fill to root at end of run)
    fThreadLocalData.Get().fIndex = 0;
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
    auto *att_edep = fInputHitsCollection->GetHitAttribute("TotalEnergyDeposit");
    auto *att_pos = fInputHitsCollection->GetHitAttribute("PostPosition");
    auto *att_vid = fInputHitsCollection->GetHitAttribute("PreStepUniqueVolumeID");
    auto *att_time = fInputHitsCollection->GetHitAttribute("GlobalTime");
    l.fInputEdep = &att_edep->GetDValues();
    l.fInputPos = &att_pos->Get3Values();
    l.fInputVolumeId = &att_vid->GetUValues();
    l.fInputTime = &att_time->GetDValues();
}

void GamHitsAdderActor::EndOfEventAction(const G4Event * /*unused*/) {
    // Get thread local variables
    auto &l = fThreadLocalData.Get();

    // Consider all hits in the current event
    auto &fIndex = l.fIndex;
    auto n = fInputHitsCollection->GetSize() - fIndex;

    // If no new hits, do nothing
    if (n <= 0) return;

    // Loop on all hits in this event, and merge them if they occur in the same volume
    for (size_t i = fIndex; i < fInputHitsCollection->GetSize(); i++) {
        AddHitPerVolume(i);
    }

    // create the output hits collection for aggregated (by volume) hits
    for (auto &h: l.fMapOfHitsInVolume) {
        auto &hit = h.second;
        // terminate the merge
        hit.Terminate(fPolicy);
        // Don't store if edep is zero
        // (all "Fill" calls are thread local)
        if (hit.fFinalEdep > 0) {
            l.fOutputEdepAttribute->FillDValue(hit.fFinalEdep);
            l.fOutputPosAttribute->Fill3Value(hit.fFinalPosition);
            l.fOutputGlobalTimeAttribute->FillDValue(hit.fFinalTime);
            l.fHitsAttributeFiller->Fill(hit.fFinalIndex);
        }
    }

    // update the hits index (thread local)
    fIndex = fInputHitsCollection->GetSize();

    // reset the structure of hits
    l.fMapOfHitsInVolume.clear();
}

void GamHitsAdderActor::AddHitPerVolume(size_t i) {
    // Get thread local variables
    auto &l = fThreadLocalData.Get();
    auto edep = (*l.fInputEdep)[i];
    auto pos = (*l.fInputPos)[i];
    auto volID = (*l.fInputVolumeId)[i];
    auto time = (*l.fInputTime)[i];

    // do not store anything if edep == 0
    if (edep == 0) return;

    // Is the current volume already seen ? If not, create the struct
    if (l.fMapOfHitsInVolume.count(volID) == 0) {
        l.fMapOfHitsInVolume[volID] = GamHitsAdderInVolume();
    }
    l.fMapOfHitsInVolume[volID].Update(fPolicy, i, edep, pos, time);
}


// Called every time a Run ends
void GamHitsAdderActor::EndOfRunAction(const G4Run * /*unused*/) {
    DD("End of run");
    DDD(fOutputHitsCollection->GetSize());
    fOutputHitsCollection->FillToRoot();

    auto *man = GamUniqueVolumeIDManager::GetInstance();
    for (auto &m: man->GetAllVolumeIDs()) {
        DDD(m.first);
        DD(m.second->fID);
    }

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

