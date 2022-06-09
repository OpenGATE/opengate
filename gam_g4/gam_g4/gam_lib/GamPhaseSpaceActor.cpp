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
        CheckRequiredAttribute(fHits, "EventPosition");
        CheckRequiredAttribute(fHits, "EventID");
        CheckRequiredAttribute(fHits, "TrackVertexMomentumDirection");
        CheckRequiredAttribute(fHits, "TrackVertexKineticEnergy");
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
void GamPhaseSpaceActor::PreUserTrackingAction(const G4Track *track) {
    for (auto f: fFilters) {
        if (!f->Accept(track)) return;
    }
    auto &l = fThreadLocalData.Get();
    if (fEndOfEventOption and not l.currentTrackAlreadyStored) {
        l.fEventDirection = track->GetVertexMomentumDirection();
        l.fEventEnergy = track->GetKineticEnergy();
        l.currentTrackAlreadyStored = true;
    }
}

// Called every time a batch of step must be processed
void GamPhaseSpaceActor::SteppingAction(G4Step *step) {
    // Only store if this is the first time 
    if (!step->IsFirstStepInVolume()) return;
    fHits->FillHits(step);
    if (fEndOfEventOption) {
        auto &l = fThreadLocalData.Get();
        l.fCurrentEventHasBeenStored = true;
    }
}

void GamPhaseSpaceActor::EndOfEventAction(const G4Event *event) {
    auto &l = fThreadLocalData.Get();
    if (fEndOfEventOption and not l.fCurrentEventHasBeenStored) {

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

        if (!l.currentTrackAlreadyStored) {
            // random isotropic direction for filtered event
            auto x = G4UniformRand();
            auto y = G4UniformRand();
            auto z = G4UniformRand();
            l.fEventDirection = G4ThreeVector(x, y, z);
            l.fEventDirection = l.fEventDirection / l.fEventDirection.mag();
        }

        // except TrackVertexMomentumDirection and TrackVertexKineticEnergy
        att = fHits->GetHitAttribute("TrackVertexMomentumDirection");
        auto &values_dir = att->Get3Values();
        values_dir.back() = l.fEventDirection;
        att = fHits->GetHitAttribute("TrackVertexKineticEnergy");
        auto &values_en = att->GetDValues();
        values_en.back() = l.fEventEnergy;

        l.currentTrackAlreadyStored = false;
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

