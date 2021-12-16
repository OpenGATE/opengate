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
#include "G4RootAnalysisManager.hh"
#include "GamHitsCollectionActor.h"
#include "GamHitsCollection.h"
#include "GamDictHelpers.h"
#include "GamHitAttributeManager.h"


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
    //fBasketEntries = DictInt(user_info, "basket_entries");
    fHits2 = nullptr; // needed
}

GamHitsCollectionActor::~GamHitsCollectionActor() {
}


void GamHitsCollectionActor::CreateHitCollection() {
    G4AutoLock mutex(&GamHitsActorMutex); // needed !
    DDD("CreateHitCollection");
    DDD(fHits2);
    // Already done ?
    //if (fHits2 != nullptr) return;
    /* Create the HitCollection
     Warning must be created both
     - in master thread (during StartSimulationAction)
     - in slave thread (during BeginOfRun)

     Moreover, the filename must be the same for all actors
     that write a root file.

    */

    //fHits2->fUserHitAttributeNames = fUserHitAttributeNames;


    auto am = GamHitAttributeManager::GetInstance();
    auto n = G4Threading::G4GetThreadId();

    /*if (n != -1) { // not the master thread
        if (am->fTupleNameIdMap.count(fHitsCollectionName)) {
            auto threads = am->fBuildForThisThreadMap[fHitsCollectionName];
            DDD("The tuple already exist, check if need to be build or not for this WORKER thread");
            DDD(fHitsCollectionName);
            for(auto t:threads) {
                DDD(t);
                if (t == n) {
                    DDD("Already build for this worker")
                    return;
                }
            }
            DDD("not build for this thread  -> continue");
        }
    }
    else {
        DDD("MASTER THREAD ->build anyway")
    }*/

    //fHits2 = std::make_shared<GamHitsCollection>(fHitsCollectionName);
    DDD(fHits2);
    DDD(fOutputFilename);
    fHits2->SetFilename(fOutputFilename);
    //auto ok =
    fHits2->StartInitialization();
    //if (not ok) return;
    for (auto name: fUserHitAttributeNames) {
        fHits2->InitializeHitAttribute(name);
    }
    fHits2->FinishInitialization();
    DDD(fHits2);

    // debug
/*
    auto ram = G4RootAnalysisManager::Instance();
    DDD(ram);
    DDD(ram->GetFileName());
    DDD(ram->GetFirstNtupleId());
    DDD(ram->GetNofNtuples());
    */
    DDD(fHits2);

}

// Called when the simulation start
void GamHitsCollectionActor::StartSimulationAction() {
    //G4AutoLock mutex(&GamHitsActorMutex); // FIXME needed ?
    DDD("StartSimulationActor");
    fHits2 = std::make_shared<GamHitsCollection>(fHitsCollectionName);
    CreateHitCollection(); // needed here only for multithread ?
    auto am = GamHitAttributeManager::GetInstance();
    am->CreateRootTuple(fHits2);

    auto ram = G4RootAnalysisManager::Instance();
    DDD(ram);
    DDD(ram->GetFileName());
    DDD(ram->GetFirstNtupleId());
    DDD(ram->GetNofNtuples());

    DDD("end StartSimulationActor");
}

// Called when the simulation end
void GamHitsCollectionActor::EndSimulationAction() {
    // Only in main thread
    // FIXME will be do in py side
    DDD("EndSimulationAction");
    //DDD("end write root");
    auto ram = G4RootAnalysisManager::Instance();
    //fHits2->Write();
    DDD(fHits2->fNHits);
    ram->Write(); // FIXME replace with hit->Write
    //DDD("Write on");
    //ram->CloseFile();
    DDD("Close on");
    fHits2->Close(); // REQUIRED
}

// Called every time a Run starts
void GamHitsCollectionActor::BeginOfRunAction(const G4Run *run) {
    G4AutoLock mutex(&GamHitsActorMutex);
    DDD("Begin of Run");
    auto n = G4Threading::G4GetThreadId();
    auto ram = G4RootAnalysisManager::Instance();
    DDD(ram);
    //auto r = G4RunManager::GetRunManager()->GetCurrentRun();
    //if (n != -1 and run->GetRunID() == 0) {
    if (n != -1) {
        //CreateHitCollection(); //FIXME change according to run
        auto am = GamHitAttributeManager::GetInstance();
        am->CreateRootTuple(fHits2);
    }



    //auto ram = G4RootAnalysisManager::Instance();
    //DDD(ram);
    DDD(ram->GetFileName());
    DDD(ram->GetFirstNtupleId());
    DDD(ram->GetNofNtuples());
}

// Called every time a Run ends
void GamHitsCollectionActor::EndOfRunAction(const G4Run * /*run*/) {
    G4AutoLock mutex(&GamHitsActorMutex);
    DDD("end of run");
    DDD(fHits2->fNHits);
    auto n = G4Threading::G4GetThreadId();
    if (n != -1) {
        fHits2->Write();
        DDD("end WRITE");
        //fHits2->Close();

        DDD("close");
        fHits2->Close();
    }
    /*
     * // It is mandatory to check if the file is still open because several
    // actors can write on the same file, that must be close only once.
    auto ram = G4RootAnalysisManager::Instance();
    //if (ram->IsOpenFile()) {
    DD(fCurrentProcessedHitNumber);
    if (fCurrentProcessedHitNumber>0) {
        DD("Write end run");
        ram->Write(); // Warning not both here and at ProcessHits
    }
    //ram->CloseFile();
    fCurrentProcessedHitNumber = 0;
    //}
     */
}

void GamHitsCollectionActor::BeginOfEventAction(const G4Event */*event*/) {
    //DDD("GamHitsCollectionActor::BeginOfEventAction");
}

void GamHitsCollectionActor::EndOfEventAction(const G4Event *) {

    // FIXME Write every event ?
}

// Called every time a Track starts
void GamHitsCollectionActor::PreUserTrackingAction(const G4Track */*track*/) {


}

// Called every time a batch of step must be processed
void GamHitsCollectionActor::SteppingAction(G4Step *step, G4TouchableHistory *touchable) {
    //DDD("SteppingAction");
    G4AutoLock mutex(&GamHitsActorMutex); // FIXME needed ?
    //fHits->FillStep(step, touchable);
    fHits2->ProcessHits(step, touchable);

    /*if (fCurrentProcessedHitNumber > fBasketEntries) {
        auto ram = G4RootAnalysisManager::Instance();
        DDD("Write");
        DDD(fCurrentProcessedHitNumber);
        ram->Write();
        fCurrentProcessedHitNumber = 0;
    } else fCurrentProcessedHitNumber++;
     */
    //DDD("end SteppingAction");
}

std::shared_ptr<GamTree> GamHitsCollectionActor::GetHits() {
    // FIXME
    return nullptr;//fHits2;
}