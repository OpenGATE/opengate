/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include <iostream>
#include "GamHitsCollectionActor.h"
#include "GamHitAttributeManager.h"
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
    fHitsCollectionName = DictStr(user_info, "name");
    fUserHitAttributeNames = DictVecStr(user_info, "attributes");
    fHits = nullptr;
}

GamHitsCollectionActor::~GamHitsCollectionActor() {
}


void GamHitsCollectionActor::CreateHitsCollection() {
    DDD("CreateHitsCollection");
    G4AutoLock mutex(&GamHitsActorMutex); // needed !
    fHits = std::make_shared<GamHitsCollection>(fHitsCollectionName);
    fHits->SetFilename(fOutputFilename);
    fHits->StartInitialization();
    for (auto name: fUserHitAttributeNames) {
        fHits->InitializeHitAttribute(name);
    }
    fHits->FinishInitialization();
}

// Called when the simulation start
void GamHitsCollectionActor::StartSimulationAction() {
    DDD("StartSimulationActor");
    CreateHitsCollection();
    // When MT, the following is required on:
    // - master (StartSimulationAction)
    // - workers (BeginOfRunAction)
    auto am = GamHitAttributeManager::GetInstance();
    am->CreateRootTuple(fHits);
}

// Called when the simulation end
void GamHitsCollectionActor::EndSimulationAction() {
    DDD("EndSimulationAction");
    fHits->Write();
    fHits->Close();
}

// Called every time a Run starts
void GamHitsCollectionActor::BeginOfRunAction(const G4Run * /*run*/) {
    G4AutoLock mutex(&GamHitsActorMutex);
    auto n = G4Threading::G4GetThreadId();
    if (n != -1) {
        // Create Root only for workers
        auto am = GamHitAttributeManager::GetInstance();
        am->CreateRootTuple(fHits);
    }
}

// Called every time a Run ends
void GamHitsCollectionActor::EndOfRunAction(const G4Run * /*run*/) {
    G4AutoLock mutex(&GamHitsActorMutex);
    auto n = G4Threading::G4GetThreadId();
    // Write Root only for workers
    if (n != -1) {
        fHits->Write();
    }
}

void GamHitsCollectionActor::BeginOfEventAction(const G4Event */*event*/) {
    //DDD("GamHitsCollectionActor::BeginOfEventAction");
}

void GamHitsCollectionActor::EndOfEventAction(const G4Event *) {
    // Cannot manage to Write to Root at EndOfEventAction in MT mode
}

// Called every time a Track starts
void GamHitsCollectionActor::PreUserTrackingAction(const G4Track */*track*/) {
}

// Called every time a batch of step must be processed
void GamHitsCollectionActor::SteppingAction(G4Step *step, G4TouchableHistory *touchable) {
    G4AutoLock mutex(&GamHitsActorMutex); // FIXME needed ?
    fHits->ProcessHits(step, touchable);
}

/*
std::shared_ptr<GamTree> GamHitsCollectionActor::GetHits() {
    // FIXME
    return nullptr;//fHits;
}*/