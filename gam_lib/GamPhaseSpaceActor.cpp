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
    fActions.insert("BeginOfEventAction");
    fActions.insert("PreUserTrackingAction");
    fActions.insert("SteppingAction");
    fOutputFilename = DictStr(user_info, "output");
    GamBranches::BuildAllBranches(); // FIXME

    // FIXME FIXME FIXME !!!!!!!!!!!!!!!!!!!!!!!
    GamBranches::AddFillStep("TimeFromBeginOfEvent", 'D', STEP_FILL_FUNCTION {
        auto t = step->GetTrack()->GetGlobalTime() - fBeginOfEventTimePerThread[GetThreadIndex()];
        am->FillNtupleDColumn(e.i, t);
    });

    GamBranches::AddFillStep("TrackEnergy", 'D', STEP_FILL_FUNCTION {
        auto energy = fTrackEnergyPerThread[GetThreadIndex()];
        am->FillNtupleDColumn(e.i, energy);
    });

    GamBranches::AddFillStep("EventPosition", '3', STEP_FILL_FUNCTION {
        auto p = fEventPositionPerThread[GetThreadIndex()];
        am->FillNtupleDColumn(e.i, p[0]);
        am->FillNtupleDColumn(e.i + 1, p[1]);
        am->FillNtupleDColumn(e.i + 2, p[2]);
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

    // resize according to number of thread
    // Warning : zero if mono thread
    // Warning :in multithread, start at 1, not zero !
    auto n = G4Threading::GetNumberOfRunningWorkerThreads();
    if (n == 0) n = 1;
    fBeginOfEventTimePerThread.resize(n + 1);
    fTrackEnergyPerThread.resize(n + 1);
    fEventPositionPerThread.resize(n + 1);
}

// Called when the simulation end
void GamPhaseSpaceActor::EndSimulationAction() {
    DDD("write root");
    DDD(fOutputFilename);
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

void GamPhaseSpaceActor::BeginOfEventAction(const G4Event *event) {
    G4AutoLock mutex(&GamPhaseSpaceActorMutex);
    auto pv = event->GetPrimaryVertex(0); // consider only one FIXME ?
    fEventPositionPerThread[GetThreadIndex()] = pv->GetPosition();
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
        G4AutoLock mutex(&GamPhaseSpaceActorMutex);
        fBeginOfEventTimePerThread[GetThreadIndex()] = track->GetGlobalTime();
        //auto i = G4Threading::G4GetThreadId() == -1 ? 0 : G4Threading::G4GetThreadId();
        //fBeginOfEventTimePerThread[i] = track->GetGlobalTime();
        //DDD(fBeginOfEventTime);
        fTrackEnergyPerThread[GetThreadIndex()] = track->GetKineticEnergy();
    }
}

// Called every time a batch of step must be processed
void GamPhaseSpaceActor::SteppingAction(G4Step *step, G4TouchableHistory *touchable) {
    G4AutoLock mutex(&GamPhaseSpaceActorMutex);
    for (auto element:fStepSelectedBranches) { // FIXME move as one single fFillStep in Branches ?
        element.fill(fAnalysisManager, element, step, touchable);
    }
    // this is needed to stop current tuple fill (for vector for example)
    //DDD(step->GetPostStepPoint()->GetKineticEnergy());
    fAnalysisManager->AddNtupleRow();
}
