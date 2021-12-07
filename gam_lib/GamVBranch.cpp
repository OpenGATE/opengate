/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamVBranch.h"
#include "GamTBranch.h"
#include "G4RunManager.hh"

std::vector<GamVBranch *> GamVBranch::fAvailableBranches;

GamVBranch::GamVBranch(std::string vname, char vtype) {
    fBranchName = vname;
    fBranchType = vtype;
}

GamVBranch::~GamVBranch() {
}

GamBranch<double> *GamVBranch::GetAsDoubleBranch() {
    return static_cast<GamBranch<double> *>(this);
}

GamBranch<int> *GamVBranch::GetAsIntBranch() {
    return static_cast<GamBranch<int> *>(this);
}


GamBranch<G4ThreeVector> *GamVBranch::GetAsThreeVectorBranch() {
    return static_cast<GamBranch<G4ThreeVector> *>(this);
}

GamBranch<std::string> *GamVBranch::GetAsStringBranch() {
    return static_cast<GamBranch<std::string> *>(this);
}


void GamVBranch::push_back_double(double d) {
    auto bv = GetAsDoubleBranch();
    bv->values.push_back(d);
}

void GamVBranch::push_back_int(int d) {
    auto bv = GetAsIntBranch();
    bv->values.push_back(d);
}

void GamVBranch::InitAvailableBranches() {
    // Try to keep Geant4 names as much as possible
    DefineBranch("KineticEnergy", 'D',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                     branch->push_back_double(step->GetPostStepPoint()->GetKineticEnergy());
                 }
    );
    DefineBranch("TotalEnergyDeposit", 'D',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                     branch->push_back_double(step->GetTotalEnergyDeposit());
                 }
    );
    DefineBranch("PostDirection", '3',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                     auto bv = branch->GetAsThreeVectorBranch();
                     bv->values.push_back(step->GetPostStepPoint()->GetMomentumDirection());
                 }
    );
    DefineBranch("PostPosition", '3',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                     auto bv = branch->GetAsThreeVectorBranch();
                     bv->values.push_back(step->GetPostStepPoint()->GetPosition());
                 }
    );
    DefineBranch("TrackPosition", '3',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                     auto bv = branch->GetAsThreeVectorBranch();
                     bv->values.push_back(step->GetTrack()->GetVertexPosition());
                 }
    );
    DefineBranch("LocalTime", 'D',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                     // Time since the current track is created
                     branch->push_back_double(step->GetPostStepPoint()->GetLocalTime());
                 }
    );
    DefineBranch("GlobalTime", 'D',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                     // Time since the event in which the track belongs is created
                     branch->push_back_double(step->GetPostStepPoint()->GetGlobalTime());
                 }
    );
    DefineBranch("ProperTime", 'D',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                     // Proper time of the current track
                     branch->push_back_double(step->GetPostStepPoint()->GetProperTime());
                 }
    );
    DefineBranch("TimeFromBeginOfEvent", 'D',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                     auto ev = G4RunManager::GetRunManager()->GetCurrentEvent();
                     auto pv = ev->GetPrimaryVertex(0);
                     auto time = pv->GetT0();
                     auto t = step->GetTrack()->GetGlobalTime() - time;
                     branch->push_back_double(t);
                 }
    );
    DefineBranch("StepVolumeName", 'S',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                     auto bv = branch->GetAsStringBranch();
                     auto n = step->GetPreStepPoint()->GetPhysicalVolume()->GetName();
                     bv->values.push_back(n);
                 }
    );
    DefineBranch("EventID", 'D', // FIXME warning, no Int output ?
                 [=](GamVBranch *branch, G4Step *, G4TouchableHistory *) {
                     auto ev = G4RunManager::GetRunManager()->GetCurrentEvent();
                     branch->push_back_double(ev->GetEventID());
                 }
    );
    DefineBranch("Weight", 'D',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                     branch->push_back_double(step->GetTrack()->GetWeight());
                 }
    );
    DefineBranch("EventPosition", '3',
                 [=](GamVBranch *branch, G4Step *, G4TouchableHistory *) {
                     auto ev = G4RunManager::GetRunManager()->GetCurrentEvent();
                     auto pv = ev->GetPrimaryVertex(0); // FIXME what if several vertices ?
                     auto bv = branch->GetAsThreeVectorBranch();
                     bv->values.push_back(pv->GetPosition());
                 }
    );
    DefineBranch("CreatorProcess", 'S',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                     auto bv = branch->GetAsStringBranch();
                     auto p = step->GetTrack()->GetCreatorProcess()->GetProcessName();
                     bv->values.push_back(p);
                 }
    );
}

GamVBranch *GamVBranch::CreateBranch(std::string vname, char vtype, const StepFillFunction &f) {
    GamVBranch *b = nullptr;
    if (vtype == 'D')
        b = new GamBranch<double>(vname, vtype);
    if (vtype == 'I')
        b = new GamBranch<int>(vname, vtype);
    if (vtype == '3')
        b = new GamBranch<G4ThreeVector>(vname, vtype);
    if (vtype == 'S')
        b = new GamBranch<std::string>(vname, vtype);
    if (b == nullptr) {
        std::ostringstream oss;
        oss << "Cannot create a branch of unknown type" << vtype
            << ". Known types are: D 3 I S";
        Fatal(oss.str());
    }
    b->fFillStep = f;
    b->fBranchId = -1; // must be modified when inserted in a Tree
    return b;
}

GamVBranch *GamVBranch::DefineBranch(std::string vname, char vtype, const StepFillFunction &f) {
    // FIXME check type
    auto b = CreateBranch(vname, vtype, f);
    // FIXME check not already exist
    //if (vname != "MyBranch")
    GamVBranch::fAvailableBranches.push_back(b);
    //GamVBranch::fAvailableBranches[fCurrentNumberOfAvailableBranches] = b;
    //fCurrentNumberOfAvailableBranches++;
    return b;
}

GamVBranch *GamVBranch::CreateBranchCopy() {
    auto b = CreateBranch(fBranchName, fBranchType, fFillStep);
    return b;
}

void GamVBranch::FillStep(G4Step *step, G4TouchableHistory *history) {
    fFillStep(this, step, history);
}

std::string GamVBranch::DumpAvailableBranchesList() {
    std::ostringstream oss;
    for (auto branch: GamVBranch::fAvailableBranches)
        oss << branch->fBranchName << " ";
    return oss.str();
}

void GamVBranch::FreeAvailableBranches() {
    for (auto branch: GamVBranch::fAvailableBranches) {
        //std::cout << "deleting " << branch->fBranchName << " " << std::endl;
        delete branch;
    }
    //py::gil_scoped_release release;
}
