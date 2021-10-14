/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamVBranch.h"
#include "GamTBranch.h"

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
    DefineBranch("LocalTime", 'D',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                     branch->push_back_double(step->GetPostStepPoint()->GetLocalTime());
                 }
    );
    DefineBranch("GlobalTime", 'D',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                     branch->push_back_double(step->GetPostStepPoint()->GetGlobalTime());
                 }
    );
    DefineBranch("ProperTime", 'D',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                     branch->push_back_double(step->GetPostStepPoint()->GetProperTime());
                 }
    );
    /*DefineBranch("TimeFromBeginOfEvent", 'D',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *, GamVActor * actor) {
                    
                     auto t = step->GetTrack()->GetGlobalTime() - fBeginOfEventTimePerThread[GetThreadIndex()];
                     branch->push_back_double(t);
                 }
    );*/
    DefineBranch("VolumeName", 'S',
                 [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                     auto bv = branch->GetAsStringBranch();
                     auto n = step->GetTrack()->GetVolume()->GetName();
                     bv->values.push_back(n);
                 }
    );
}

GamVBranch *GamVBranch::CreateBranch(std::string vname, char vtype, const StepFillFunction &f) {
    GamVBranch *b = nullptr;
    if (vtype == 'D')
        b = new GamBranch<double>(vname, vtype);
    //b = std::make_shared<GamBranch<double>>(vname, vtype).get();
    if (vtype == '3')
        b = new GamBranch<G4ThreeVector>(vname, vtype);
    if (vtype == 'S')
        b = new GamBranch<std::string>(vname, vtype);
    if (b == nullptr) {
        std::ostringstream oss;
        oss << "Cannot create a branch of unknown type" << vtype
            << ". Known types are: D 3 I ";
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
    for (auto branch:GamVBranch::fAvailableBranches)
        oss << branch->fBranchName << " ";
    return oss.str();
}

void GamVBranch::FreeAvailableBranches() {
    for (auto branch:GamVBranch::fAvailableBranches) {
        //std::cout << "deleting " << branch->fBranchName << " " << std::endl;
        delete branch;
    }
    //py::gil_scoped_release release;
}
