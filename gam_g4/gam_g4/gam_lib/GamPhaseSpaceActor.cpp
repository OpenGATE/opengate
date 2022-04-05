/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <iostream>
#include "G4RunManager.hh"
#include "GamPhaseSpaceActor.h"
#include "GamHelpersDict.h"
#include "GamHitsCollectionManager.h"
#include "GamHelpersHits.h"

G4Mutex GamPhaseSpaceActorMutex = G4MUTEX_INITIALIZER;

GamPhaseSpaceActor::GamPhaseSpaceActor(py::dict &user_info)
        : GamVActor(user_info) {
    fActions.insert("StartSimulationAction");
    fActions.insert("BeginOfRunAction");
    fActions.insert("PreUserTrackingAction");
    fActions.insert("SteppingAction");
    fActions.insert("EndOfRunAction");
    fActions.insert("EndOfSimulationWorkerAction");
    fActions.insert("EndSimulationAction");
    fOutputFilename = DictGetStr(user_info, "output");
    fHitsCollectionName = DictGetStr(user_info, "name");
    fUserHitAttributeNames = DictGetVecStr(user_info, "attributes");
    fEndOfEventOption = DictGetBool(user_info, "phsp_gan_flag");
    fHits = nullptr;

    // Special case
    if (fEndOfEventOption) {
        fActions.insert("BeginOfEventAction");
        fActions.insert("EndOfEventAction");
        auto &l = fThreadLocalData.Get();
        l.fCurrentEventHasBeenStored = false;
    }
}

GamPhaseSpaceActor::~GamPhaseSpaceActor() {
}

// Called when the simulation start
void GamPhaseSpaceActor::StartSimulationAction() {
    fHits = GamHitsCollectionManager::GetInstance()->NewHitsCollection(fHitsCollectionName);
    fHits->SetFilename(fOutputFilename);
    fHits->InitializeHitAttributes(fUserHitAttributeNames);
    fHits->InitializeRootTupleForMaster();
    if (fEndOfEventOption) {
        CheckThatAttributeExists(fHits, "EventPosition");
        CheckThatAttributeExists(fHits, "EventID");
    }
}

// Called every time a Run starts
void GamPhaseSpaceActor::BeginOfRunAction(const G4Run *run) {
    if (run->GetRunID() == 0)
        fHits->InitializeRootTupleForWorker();
}

void GamPhaseSpaceActor::BeginOfEventAction(const G4Event *) {
    auto &l = fThreadLocalData.Get();
    l.fCurrentEventHasBeenStored = false;
}

// Called every time a Track starts (even if not in the volume attached to this actor)
void GamPhaseSpaceActor::PreUserTrackingAction(const G4Track *) {
}

// Called every time a batch of step must be processed
void GamPhaseSpaceActor::SteppingAction(G4Step *step, G4TouchableHistory *touchable) {
    // Only store if this is the first time 
    if (!step->IsFirstStepInVolume()) return;
    fHits->ProcessHits(step, touchable);
    if (fEndOfEventOption) {
        auto &l = fThreadLocalData.Get();
        l.fCurrentEventHasBeenStored = true;
    }
}

void GamPhaseSpaceActor::EndOfEventAction(const G4Event *event) {
    auto &l = fThreadLocalData.Get();
    if (not l.fCurrentEventHasBeenStored) {
        // Put empty value for all attributes
        fHits->FillHitsWithEmptyValue();
        // Except EventPosition
        auto att = fHits->GetHitAttribute("EventPosition");
        auto p = event->GetPrimaryVertex(0)->GetPosition();
        auto &values = att->Get3Values();
        values.back() = p;
        // And except EventID
        att = fHits->GetHitAttribute("EventID");
        auto &values_id = att->GetIValues();
        values_id.back() = event->GetEventID();

        /*fHits->FillHitsWithEmptyValue();
        values.back() = p;
        values_id.back() = event->GetEventID();
        */
    }
}

// Called every time a Run ends
void GamPhaseSpaceActor::EndOfRunAction(const G4Run *) {
    fHits->FillToRoot();
}

// Called every time a Run ends
void GamPhaseSpaceActor::EndOfSimulationWorkerAction(const G4Run *) {
    fHits->Write();
}

// Called when the simulation end
void GamPhaseSpaceActor::EndSimulationAction() {
    fHits->Write();
    fHits->Close();
}

