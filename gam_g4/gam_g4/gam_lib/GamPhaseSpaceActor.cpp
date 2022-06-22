/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4RunManager.hh"
#include "GamPhaseSpaceActor.h"
#include "GamHelpersDict.h"
#include "GamHitsCollectionManager.h"
#include "GamHelpersHits.h"


GamPhaseSpaceActor::GamPhaseSpaceActor(py::dict &user_info)
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
    fStoreAbsorbedEvent = DictGetBool(user_info, "store_absorbed_event");
    fDebug = DictGetBool(user_info, "debug");
    fHits = nullptr;

    // Special case to store event information even if the event do not step in the mother volume
    if (fStoreAbsorbedEvent) {
        fActions.insert("BeginOfEventAction");
        fActions.insert("EndOfEventAction");
    }
}

GamPhaseSpaceActor::~GamPhaseSpaceActor() {
    // for debug
}

// Called when the simulation start
void GamPhaseSpaceActor::StartSimulationAction() {
    fHits = GamHitsCollectionManager::GetInstance()->NewHitsCollection(fHitsCollectionName);
    fHits->SetFilename(fOutputFilename);
    fHits->InitializeHitAttributes(fUserHitAttributeNames);
    fHits->InitializeRootTupleForMaster();
    if (fStoreAbsorbedEvent) {
        CheckRequiredAttribute(fHits, "EventID");
        CheckRequiredAttribute(fHits, "EventPosition");
        CheckRequiredAttribute(fHits, "EventKineticEnergy");
        CheckRequiredAttribute(fHits, "EventDirection");
        fNumberOfAbsorbedEvents = 0;
    }
}

// Called every time a Run starts
void GamPhaseSpaceActor::BeginOfRunAction(const G4Run *run) {
    if (run->GetRunID() == 0)
        fHits->InitializeRootTupleForWorker();
}

void GamPhaseSpaceActor::BeginOfEventAction(const G4Event *) {
    if (fStoreAbsorbedEvent) {
        // The current event still have to be stored
        auto &l = fThreadLocalData.Get();
        l.fCurrentEventHasBeenStored = false;
    }
}

// Called every time a batch of step must be processed
void GamPhaseSpaceActor::SteppingAction(G4Step *step) {
    // Only store if this is the first time 
    if (!step->IsFirstStepInVolume()) return;
    fHits->FillHits(step);
    // Set that at least one step for this event have been stored
    if (fStoreAbsorbedEvent) {
        auto &l = fThreadLocalData.Get();
        l.fCurrentEventHasBeenStored = true;
    }
    if (fDebug) {
        auto s = fHits->DumpLastHit();
        auto id = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
        std::cout << GetName() << " " << id << " " << s << std::endl;
    }
}

void GamPhaseSpaceActor::EndOfEventAction(const G4Event *event) {
    // For a given event, when no step never reach the phsp:
    // if the option is on, we store a "fake" step, with the event information.
    // All other attributes will be "empty" (mostly 0)
    auto &l = fThreadLocalData.Get();
    if (fStoreAbsorbedEvent and not l.fCurrentEventHasBeenStored) {
        // Put empty value for all attributes
        fHits->FillHitsWithEmptyValue();

        // Except EventPosition
        auto *att = fHits->GetHitAttribute("EventPosition");
        auto p = event->GetPrimaryVertex(0)->GetPosition();
        auto &values = att->Get3Values();
        values.back() = p;

        // Except EventID
        att = fHits->GetHitAttribute("EventID");
        auto &values_id = att->GetIValues();
        values_id.back() = event->GetEventID();

        // Except EventDirection
        att = fHits->GetHitAttribute("EventDirection");
        auto &values_dir = att->Get3Values();
        auto d = event->GetPrimaryVertex(0)->GetPrimary(0)->GetMomentumDirection();
        values_dir.back() = d;

        // Except EventKineticEnergy
        att = fHits->GetHitAttribute("EventKineticEnergy");
        auto &values_en = att->GetDValues();
        auto e = event->GetPrimaryVertex(0)->GetPrimary(0)->GetKineticEnergy();
        values_en.back() = e;

        // increase the nb of absorbed events
        fNumberOfAbsorbedEvents++;
    }
}

// Called every time a Run ends
void GamPhaseSpaceActor::EndOfRunAction(const G4Run * /*unused*/) {
    fHits->FillToRootIfNeeded(true);
}

// Called every time a Run ends
void GamPhaseSpaceActor::EndOfSimulationWorkerAction(const G4Run * /*unused*/) {
    fHits->Write();
}

// Called when the simulation end
void GamPhaseSpaceActor::EndSimulationAction() {
    fHits->Write();
    fHits->Close();
}

