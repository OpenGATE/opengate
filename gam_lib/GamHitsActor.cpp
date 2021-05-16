/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include <chrono>
#include <vector>
#include <iomanip>
#include <iostream>
#include <sstream>
#include "G4VProcess.hh"
#include "GamHitsActor.h"
#include "GamHelpers.h"
#include "GamDictHelpers.h"

G4Mutex GamHitsActorMutex = G4MUTEX_INITIALIZER; // FIXME

GamHitsActor::GamHitsActor(py::dict &user_info)
    : GamVActor(user_info) {
    fActions.push_back("StartSimulationAction");
    fActions.push_back("EndSimulationAction");
    //fActions.push_back("BeginOfRunAction");
    //fActions.push_back("EndOfRunAction");
    //fActions.push_back("PreUserTrackingAction");
    fActions.push_back("SteppingAction");
    fOutputFilename = DictStr(user_info, "output");
    BuildAvailableElements();
}

GamHitsActor::~GamHitsActor() = default;

void GamHitsActor::BuildAvailableElements() {
    /*
     * Declaration of all available elements that user may want to store.
     * By default, they are not enabled.
     * For all elements, we need 1) a name, 2) a type, 3) a function that fill the G4GenericAnalysisManager
     *
     * The type can be D, I or S (Double, Int, String)
     *
     * The fill function is StepFillFunction (see GamHitsActor.hh)
     */

    AddFillStepElement("KineticEnergy", 'D', STEP_FILL_FUNCTION {
        am->FillNtupleDColumn(e.i, step->GetPostStepPoint()->GetKineticEnergy());
    });
    AddFillStepElement("ParticleName", 'S', STEP_FILL_FUNCTION {
        am->FillNtupleSColumn(e.i, step->GetTrack()->GetParticleDefinition()->GetParticleName());
    });
    AddFillStepElement("CreatorProcess", 'S', STEP_FILL_FUNCTION {
        am->FillNtupleSColumn(e.i, step->GetTrack()->GetCreatorProcess()->GetProcessName());
    });
    AddFillStepElement("LocalTime", 'D', STEP_FILL_FUNCTION {
        am->FillNtupleDColumn(e.i, step->GetPostStepPoint()->GetLocalTime());
    });
    AddFillStepElement("GlobalTime", 'D', STEP_FILL_FUNCTION {
        am->FillNtupleDColumn(e.i, step->GetPostStepPoint()->GetGlobalTime());
    });
    AddFillStepElement("Weight", 'D', STEP_FILL_FUNCTION {
        am->FillNtupleDColumn(e.i, step->GetTrack()->GetWeight());
    });
    AddFillStepElement("TrackID", 'I', STEP_FILL_FUNCTION {
        am->FillNtupleIColumn(e.i, step->GetTrack()->GetTrackID());
    });
    AddFillStepElement("Volume", 'S', STEP_FILL_FUNCTION {
        auto n = step->GetTrack()->GetVolume()->GetName();
        am->FillNtupleSColumn(e.i, n);
    });
    AddFillStepElement("PostPosition", '3', STEP_FILL_FUNCTION {
        am->FillNtupleDColumn(e.i, step->GetPostStepPoint()->GetPosition()[0]);
        am->FillNtupleDColumn(e.i + 1, step->GetPostStepPoint()->GetPosition()[1]);
        am->FillNtupleDColumn(e.i + 2, step->GetPostStepPoint()->GetPosition()[2]);
    });
    AddFillStepElement("PostDirection", '3', STEP_FILL_FUNCTION {
        am->FillNtupleDColumn(e.i, step->GetPostStepPoint()->GetMomentumDirection()[0]);
        am->FillNtupleDColumn(e.i + 1, step->GetPostStepPoint()->GetMomentumDirection()[1]);
        am->FillNtupleDColumn(e.i + 2, step->GetPostStepPoint()->GetMomentumDirection()[2]);
    });
}

// Called when the simulation start
void GamHitsActor::StartSimulationAction() {
    // create the file
    auto analysisManager = G4GenericAnalysisManager::Instance();
    analysisManager->OpenFile(fOutputFilename);
    // create a tree (only one for the moment)
    analysisManager->CreateNtuple("Hits", "Hits collection");
    // check branch name exist
    auto &b = fStepFillNames;
    auto &a = fStepFillAllElements;
    for (auto &branch:b) {
        auto it = std::find_if(a.begin(), a.end(),
                               [&branch](const FillStepStruct &x) { return x.name == branch; });
        if (it == a.end()) {
            std::ostringstream oss;
            oss << "The branch '" << branch << "' is unknown in GamHitsActor. Known branches are:";
            for (auto aa:a)
                oss << " " << aa.name;
            Fatal(oss.str());
        }
    }
    // enable some branches
    int i = 0;
    for (auto &e:fStepFillAllElements) {
        if (std::find(b.begin(), b.end(), e.name) != b.end()) {
            e.i = i;
            if (e.type == 'D') analysisManager->CreateNtupleDColumn(e.name);
            if (e.type == 'S') analysisManager->CreateNtupleSColumn(e.name);
            if (e.type == 'I') analysisManager->CreateNtupleIColumn(e.name);
            if (e.type == '3') {
                analysisManager->CreateNtupleDColumn(e.name + "_X");
                analysisManager->CreateNtupleDColumn(e.name + "_Y");
                analysisManager->CreateNtupleDColumn(e.name + "_Z");
                i += 2;
            }
            fStepFillEnabledElements.push_back(e);
            i++;
        }
    }
    analysisManager->FinishNtuple(); // needed to indicate the tuple is finished
}

void GamHitsActor::AddFillStepElement(std::string name, char type, StepFillFunction f) {
    if (type != 'D' and type != 'S' and type != 'I' and type != '3') {
        Fatal("Devel error in GamHitsActor::AddFillStepElement, type must be D, S, 3 or I"
              ", while it is " + std::string(1, type));
    }
    FillStepStruct t;
    t.name = name;
    t.type = type;
    t.i = -1;
    t.fill = f;
    fStepFillAllElements.push_back(t);
}

// Called when the simulation end
void GamHitsActor::EndSimulationAction() {
    auto analysisManager = G4GenericAnalysisManager::Instance();
    analysisManager->Write();
    analysisManager->CloseFile(); // not really needed
}

// Called every time a Run starts
void GamHitsActor::BeginOfRunAction(const G4Run * /*run*/) {
    //DDD("not yet");
}

// Called every time a Run ends
void GamHitsActor::EndOfRunAction(const G4Run *run) {
    //DDD("not yet");
}

// Called every time a Track starts
void GamHitsActor::PreUserTrackingAction(const G4Track *track) {
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
}

// Called every time a batch of step must be processed
void GamHitsActor::SteppingAction(G4Step *step, G4TouchableHistory *touchable) {
    // G4AutoLock mutex(&GamHitsActorMutex);
    auto analysisManager = G4GenericAnalysisManager::Instance();
    for (auto element:fStepFillEnabledElements) {
        element.fill(analysisManager, element, step, touchable);
    }
    // this is needed to stop current tuple fill (for vector for example)
    analysisManager->AddNtupleRow();
}
