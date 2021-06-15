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
#include "GamPhaseSpaceActor.h"
#include "GamHelpers.h"
#include "GamDictHelpers.h"
#include "GamBranches.h"

G4Mutex GamPhaseSpaceActorMutex = G4MUTEX_INITIALIZER; // FIXME

GamPhaseSpaceActor::GamPhaseSpaceActor(py::dict &user_info)
    : GamVActor(user_info) {
    fActions.insert("StartSimulationAction");
    fActions.insert("EndSimulationAction");
    fActions.insert("PreUserTrackingAction");
    fActions.insert("SteppingAction");
    fOutputFilename = DictStr(user_info, "output");
    GamBranches::BuildAllBranches(); // FIXME


    // FIXME FIXME FIXME !!!!!!!!!!!!!!!!!!!!!!!
    GamBranches::AddFillStep("TimeFromBeginOfEvent", 'D', STEP_FILL_FUNCTION {
        auto t = step->GetTrack()->GetGlobalTime() - fBeginOfEventTime;
        am->FillNtupleDColumn(e.i, t);
    });
    // FIXME FIXME FIXME !!!!!!!!!!!!!!!!!!!!!!!


    // Create main instance of the analysis manager
    fAnalysisManager = G4GenericAnalysisManager::Instance();
}

GamPhaseSpaceActor::~GamPhaseSpaceActor() {
}

// Called when the simulation start
void GamPhaseSpaceActor::StartSimulationAction() {
    // create the file
    fAnalysisManager->OpenFile(fOutputFilename);
    fAnalysisManager->SetNtupleMerging(true);
    // create a tree (only one for the moment)
    fAnalysisManager->CreateNtuple("PhaseSpace", "Hits collection");
    fStepSelectedBranches.clear();
    GamBranches::GetSelectedBranches(fStepFillNames, fAnalysisManager, fStepSelectedBranches);
    fAnalysisManager->FinishNtuple(); // needed to indicate the tuple is finished
}

// Called when the simulation end
void GamPhaseSpaceActor::EndSimulationAction() {
    fAnalysisManager->Write();
    fAnalysisManager->CloseFile(); // not really needed
}

// Called every time a Run starts
void GamPhaseSpaceActor::BeginOfRunAction(const G4Run * /*run*/) {
    //DDD("not yet");
}

// Called every time a Run ends
void GamPhaseSpaceActor::EndOfRunAction(const G4Run * /*run*/) {
    //DDD("not yet");
}

void GamPhaseSpaceActor::BeginOfEventAction(const G4Event */*event*/) {
    //fBeginOfEventTime = event->Get
}

// Called every time a Track starts
void GamPhaseSpaceActor::PreUserTrackingAction(const G4Track *track) {
    /*
    auto n = track->GetParticleDefinition()->GetParticleName();
    if (n != "gamma") return;
    DDD("PreUserTrackingAction");
    DDD(track->GetTrackID());
    DDD(track->GetPosition());
    DDD(track->GetMomentumDirection());
    DDD(track->GetKineticEnergy());
    DDD(track->GetVolume()->GetName());
    DDD(track->GetParticleDefinition()->GetParticleName());
    DDD(track->GetCreatorProcess()->GetProcessName());
     */
    if (track->GetTrackID() == 1) { // first track (event start)
        fBeginOfEventTime = track->GetGlobalTime();
    }
}

// Called every time a batch of step must be processed
void GamPhaseSpaceActor::SteppingAction(G4Step *step, G4TouchableHistory *touchable) {
    G4AutoLock mutex(&GamPhaseSpaceActorMutex);
    for (auto element:fStepSelectedBranches) { // FIXME move as one single Fill in Branches ?
        element.fill(fAnalysisManager, element, step, touchable);
    }
    // this is needed to stop current tuple fill (for vector for example)
    fAnalysisManager->AddNtupleRow();
}
