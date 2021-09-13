/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include <vector>
#include <iostream>
#include "G4VProcess.hh"
#include "G4GenericAnalysisManager.hh"
#include "G4RunManager.hh"
#include "GamHitsCollectionActor.h"
#include "GamDictHelpers.h"


G4Mutex GamHitsActorMutex = G4MUTEX_INITIALIZER; // FIXME

GamHitsCollectionActor::GamHitsCollectionActor(py::dict &user_info)
    : GamVActor(user_info) {
    fActions.insert("StartSimulationAction");
    fActions.insert("EndSimulationAction");
    fActions.insert("BeginOfRunAction");
    fActions.insert("EndOfRunAction");
    //fActions.insert("PreUserTrackingAction");
    //fActions.insert("EndOfEventAction");
    fActions.insert("SteppingAction");
    fOutputFilename = DictStr(user_info, "output");
    fUserBranchNames = DictVecStr(user_info, "branches");
}

GamHitsCollectionActor::~GamHitsCollectionActor() {
}

// Called when the simulation start
void GamHitsCollectionActor::StartSimulationAction() {
    GamVBranch::InitAvailableBranches();

    // add all branches defined by the user
    fHits = std::make_shared<GamTree>("Hits");
    for (auto branch_name:fUserBranchNames) {
        fHits->AddBranch(branch_name);
    }
}

// Called when the simulation end
void GamHitsCollectionActor::EndSimulationAction() {
    // FIXME will be do in py side
    //DDD("EndSimulationAction");
    //DDD(fHits->Dump());
    //fHits->WriteToRoot(fOutputFilename);
    //DDD("end write root");
}

// Called every time a Run starts
void GamHitsCollectionActor::BeginOfRunAction(const G4Run * /*run*/) {
    // DDD("Begin of Run");
}

// Called every time a Run ends
void GamHitsCollectionActor::EndOfRunAction(const G4Run * /*run*/) {
    // DDD("end of run");
}

void GamHitsCollectionActor::BeginOfEventAction(const G4Event */*event*/) {
    //DDD("GamHitsCollectionActor::BeginOfEventAction");
}

void GamHitsCollectionActor::EndOfEventAction(const G4Event *) {
}

// Called every time a Track starts
void GamHitsCollectionActor::PreUserTrackingAction(const G4Track */*track*/) {

}

// Called every time a batch of step must be processed
void GamHitsCollectionActor::SteppingAction(G4Step *step, G4TouchableHistory *touchable) {
    G4AutoLock mutex(&GamHitsActorMutex);
    fHits->FillStep(step, touchable);
}
