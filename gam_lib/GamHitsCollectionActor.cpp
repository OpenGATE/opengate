/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <iostream>
#include "G4RunManager.hh"
#include "GamHitsCollectionActor.h"
#include "GamDictHelpers.h"
#include "GamHitsCollectionManager.h"

GamHitsCollectionActor::GamHitsCollectionActor(py::dict &user_info)
    : GamVActor(user_info) {
    fActions.insert("StartSimulationAction");
    fActions.insert("BeginOfRunAction");
    fActions.insert("SteppingAction");
    fActions.insert("EndOfRunAction");
    fActions.insert("EndOfSimulationWorkerAction");
    fActions.insert("EndSimulationAction");
    fOutputFilename = DictStr(user_info, "output");
    fHitsCollectionName = DictStr(user_info, "name");
    fUserHitAttributeNames = DictVecStr(user_info, "attributes");
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

void GamHitsCollectionActor::BeginOfEventAction(const G4Event *) {
    // nothing
}

// Called every time a Track starts
void GamHitsCollectionActor::PreUserTrackingAction(const G4Track *) {
}

// Called every time a batch of step must be processed
void GamHitsCollectionActor::SteppingAction(G4Step *step, G4TouchableHistory *touchable) {
    fHits->ProcessHits(step, touchable);
}

void GamHitsCollectionActor::EndOfEventAction(const G4Event *) {
    // nothing
}

// Called every time a Run ends
void GamHitsCollectionActor::EndOfRunAction(const G4Run *) {
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

