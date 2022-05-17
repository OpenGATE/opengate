/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4RunManager.hh"
#include "GamHitsCollectionActor.h"
#include "GamHelpersDict.h"
#include "GamHitsCollectionManager.h"
#include "GamUniqueVolumeIDManager.h"

GamHitsCollectionActor::GamHitsCollectionActor(py::dict &user_info)
    : GamVActor(user_info) {
    fActions.insert("StartSimulationAction");
    fActions.insert("BeginOfRunAction");
    fActions.insert("SteppingAction");
    fActions.insert("EndOfRunAction");
    fActions.insert("EndOfSimulationWorkerAction");
    fActions.insert("EndSimulationAction");
    fOutputFilename = DictGetStr(user_info, "output");
    fHitsCollectionName = DictGetStr(user_info, "name");
    fUserHitAttributeNames = DictGetVecStr(user_info, "attributes");
    fHits = nullptr;
}

GamHitsCollectionActor::~GamHitsCollectionActor() {
}

// Called when the simulation start
void GamHitsCollectionActor::StartSimulationAction() {
    fHits = GamHitsCollectionManager::GetInstance()->NewHitsCollection(fHitsCollectionName);
    // This order is important: filename and attributes must be set before Root initialization
    fHits->SetFilename(fOutputFilename);
    fHits->InitializeHitAttributes(fUserHitAttributeNames);
    fHits->InitializeRootTupleForMaster();
}

// Called every time a Run starts
void GamHitsCollectionActor::BeginOfRunAction(const G4Run *run) {
    // Needed to create the root output (only the first run)
    if (run->GetRunID() == 0)
        fHits->InitializeRootTupleForWorker();
}

// Called every time a batch of step must be processed
void GamHitsCollectionActor::SteppingAction(G4Step *step) {

    /*
    // fixme debug
    auto eid = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
    auto aid = step->GetTrack()->GetTrackID();
    //if (eid >= 20 and aid == 2) {
    DDD(eid);
    DDD(aid);
    DDD(step->GetPreStepPoint()->GetPosition());
    DDD(step->GetPostStepPoint()->GetPosition());
    DDD(step->GetPostStepPoint()->GetProcessDefinedStep()->GetProcessName());
    DDD(step->GetTrack()->GetVolume()->GetCopyNo());
    auto touchable = step->GetPreStepPoint()->GetTouchable();
    auto depth1 = touchable->GetHistoryDepth();
    auto copyNb = touchable->GetVolume(depth1)->GetCopyNo();
    DDD(copyNb);
    touchable = step->GetPostStepPoint()->GetTouchable();
    auto depth2 = touchable->GetHistoryDepth();
    copyNb = touchable->GetVolume(depth2)->GetCopyNo();
    DDD(copyNb);
    DDD(step->GetTotalEnergyDeposit());
    DDD(step->GetPostStepPoint()->GetKineticEnergy());
    auto *m = GamUniqueVolumeIDManager::GetInstance();
    auto uid = m->GetVolumeID(step->GetPreStepPoint()->GetTouchable());
    DDD(uid->fID);
    uid = m->GetVolumeID(step->GetPostStepPoint()->GetTouchable());
    DDD(uid->fID);

    // post
    DDD(step->GetPreStepPoint()->GetTouchable()->GetVolume(depth1)->GetLogicalVolume()->GetSolid()->GetCubicVolume());
    DDD(step->GetPostStepPoint()->GetTouchable()->GetVolume(depth2)->GetLogicalVolume()->GetSolid()->GetCubicVolume());

    DDD(step->GetPreStepPoint()->GetTouchable()->GetVolume(depth1)->GetTranslation());
    DDD(step->GetPostStepPoint()->GetTouchable()->GetVolume(depth2)->GetTranslation());

    //   }
     */

    // Do not store step with zero edep
    if (step->GetTotalEnergyDeposit() > 0)
        fHits->FillHits(step);
}

// Called every time a Run ends
void GamHitsCollectionActor::EndOfRunAction(const G4Run * /*unused*/) {
    /*
     * For the moment, we consider flushing values every run.
     * If a process need to access hits across different run, this should be move in
     * EndOfSimulationWorkerAction.
     */
    // Copy value to root (need to clear !)
    fHits->FillToRoot();
}

void GamHitsCollectionActor::EndOfSimulationWorkerAction(const G4Run * /*lastRun*/) {
    // Write only once per worker thread
    fHits->Write();
}

// Called when the simulation end
void GamHitsCollectionActor::EndSimulationAction() {
    fHits->Write();
    fHits->Close();
}

