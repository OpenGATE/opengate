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
#include "GamHelpers.h"
#include "GamDictHelpers.h"
#include "GamBranches.h"

// init static variable
std::vector<GamBranches::BranchFillStepStruct> GamBranches::fAllBranches;

GamBranches::~GamBranches() {
}

void GamBranches::BuildAllBranches() {

    // only once
    if (GamBranches::fAllBranches.size() > 0) return;

    /*
     * Declaration of all available elements that user may want to store.
     * By default, they are not enabled.
     * For all elements, we need 1) a name, 2) a type, 3) a function that fill the G4GenericfAnalysisManager
     *
     * The type can be D, I or S (Double, Int, String)
     *
     * The fill function is StepFillFunction (see GamPhaseSpaceActor.hh)
     */

    GamBranches::AddFillStep("KineticEnergy", 'D', STEP_FILL_FUNCTION {
        am->FillNtupleDColumn(e.i, step->GetPostStepPoint()->GetKineticEnergy());
    });
    GamBranches::AddFillStep("ParticleName", 'S', STEP_FILL_FUNCTION {
        am->FillNtupleSColumn(e.i, step->GetTrack()->GetParticleDefinition()->GetParticleName());
    });
    GamBranches::AddFillStep("CreatorProcess", 'S', STEP_FILL_FUNCTION {
        am->FillNtupleSColumn(e.i, step->GetTrack()->GetCreatorProcess()->GetProcessName());
    });
    GamBranches::AddFillStep("LocalTime", 'D', STEP_FILL_FUNCTION {
        am->FillNtupleDColumn(e.i, step->GetPostStepPoint()->GetLocalTime());
    });
    /*GamBranches::AddFillStep("TimeFromBeginOfEvent", 'D', STEP_FILL_FUNCTION {
        auto t = step->GetTrack()->GetGlobalTime() - fBeginOfEventTime; // FIXME FIXME FIXME
        am->FillNtupleDColumn(e.i, t);
    });*/
    GamBranches::AddFillStep("GlobalTime", 'D', STEP_FILL_FUNCTION {
        am->FillNtupleDColumn(e.i, step->GetPostStepPoint()->GetGlobalTime());
    });
    GamBranches::AddFillStep("Weight", 'D', STEP_FILL_FUNCTION {
        am->FillNtupleDColumn(e.i, step->GetTrack()->GetWeight());
    });
    GamBranches::AddFillStep("TrackID", 'I', STEP_FILL_FUNCTION {
        am->FillNtupleIColumn(e.i, step->GetTrack()->GetTrackID());
    });
    GamBranches::AddFillStep("EventID", 'I', STEP_FILL_FUNCTION2 {
        am->FillNtupleIColumn(e.i, G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID());
    });
    GamBranches::AddFillStep("RunID", 'I', STEP_FILL_FUNCTION2 {
        am->FillNtupleIColumn(e.i, G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID());
    });
    GamBranches::AddFillStep("Volume", 'S', STEP_FILL_FUNCTION {
        auto n = step->GetTrack()->GetVolume()->GetName();
        am->FillNtupleSColumn(e.i, n);
    });
    GamBranches::AddFillStep("CreatorProcess", 'S', STEP_FILL_FUNCTION {
        auto p = step->GetTrack()->GetCreatorProcess()->GetProcessName();
        am->FillNtupleSColumn(e.i, p);
    });
    GamBranches::AddFillStep("PostPosition", '3', STEP_FILL_FUNCTION {
        am->FillNtupleDColumn(e.i, step->GetPostStepPoint()->GetPosition()[0]);
        am->FillNtupleDColumn(e.i + 1, step->GetPostStepPoint()->GetPosition()[1]);
        am->FillNtupleDColumn(e.i + 2, step->GetPostStepPoint()->GetPosition()[2]);
    });
    GamBranches::AddFillStep("PostDirection", '3', STEP_FILL_FUNCTION {
        am->FillNtupleDColumn(e.i, step->GetPostStepPoint()->GetMomentumDirection()[0]);
        am->FillNtupleDColumn(e.i + 1, step->GetPostStepPoint()->GetMomentumDirection()[1]);
        am->FillNtupleDColumn(e.i + 2, step->GetPostStepPoint()->GetMomentumDirection()[2]);
    });
}

void GamBranches::AddFillStep(std::string name, char type, StepFillFunction f) {
    if (type != 'D' and type != 'S' and type != 'I' and type != '3') {
        Fatal("Devel error in GamBranches::GamBranches::AddFillStep, type must be D, S, 3 or I"
              ", while it is " + std::string(1, type));
    }
    BranchFillStepStruct t;
    t.name = name;
    t.type = type;
    t.i = -1;
    t.fill = f;
    GamBranches::fAllBranches.push_back(t);
}

void GamBranches::GetSelectedBranches(const std::vector<std::string> &names,
                                      G4ToolsAnalysisManager *analysisManager,
                                      std::vector<BranchFillStepStruct> &selectedBranches) {
    // check empty ?
    if (names.size() == 0) {
        Fatal("Error in GamBranches: empty list of branches");
    }
    // check branch name exist
    auto &a = GamBranches::fAllBranches;
    for (auto &branch:names) {
        auto it = std::find_if(a.begin(), a.end(),
                               [&branch](const GamBranches::BranchFillStepStruct &x) { return x.name == branch; });
        if (it == a.end()) {
            std::ostringstream oss;
            oss << "The branch '" << branch << "' is unknown. Known branches are:";
            for (auto aa:a)
                oss << " " << aa.name;
            Fatal(oss.str());
        }
    }
    // enable some branches
    int i = 0;
    for (auto &e:GamBranches::fAllBranches) {
        if (std::find(names.begin(), names.end(), e.name) != names.end()) {
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
            selectedBranches.push_back(e);
            i++;
        }
    }
}