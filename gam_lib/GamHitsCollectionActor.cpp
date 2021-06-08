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
#include "GamHelpers.h"
#include "GamDictHelpers.h"
#include "GamBranches.h"

G4Mutex GamHitsActorMutex = G4MUTEX_INITIALIZER; // FIXME

GamHitsCollectionActor::GamHitsCollectionActor(py::dict &user_info)
    : GamVActor(user_info) {
    fActions.insert("StartSimulationAction");
    fActions.insert("EndSimulationAction");
    //fActions.insert("BeginOfRunAction");
    //fActions.insert("EndOfRunAction");
    fActions.insert("PreUserTrackingAction");
    fActions.insert("EndOfEventAction");
    fActions.insert("SteppingAction");

    for (auto a:fActions) {
        DDD(a);
    }

    fOutputFilename = DictStr(user_info, "output");
    GamBranches::BuildAllBranches(); //FIXME
    // Create main instance of the analysis manager
    fAnalysisManager = G4GenericAnalysisManager::Instance();
}

GamHitsCollectionActor::~GamHitsCollectionActor() {
}

// Called when the simulation start
void GamHitsCollectionActor::StartSimulationAction() {
    DDD("later")
}

// Called when the simulation end
void GamHitsCollectionActor::EndSimulationAction() {

}

// Called every time a Run starts
void GamHitsCollectionActor::BeginOfRunAction(const G4Run * /*run*/) {
    //DDD("not yet");
}

// Called every time a Run ends
void GamHitsCollectionActor::EndOfRunAction(const G4Run * /*run*/) {
    DDD("end run");
}

void GamHitsCollectionActor::BeginOfEventAction(const G4Event */*event*/) {
    //fBeginOfEventTime = event->Get
}

void GamHitsCollectionActor::EndOfEventAction(const G4Event *) {
    //fBeginOfEventTime = event->Get
}

// Called every time a Track starts
void GamHitsCollectionActor::PreUserTrackingAction(const G4Track *track) {

}

// Called every time a batch of step must be processed
void GamHitsCollectionActor::SteppingAction(G4Step *step, G4TouchableHistory *touchable) {

}
