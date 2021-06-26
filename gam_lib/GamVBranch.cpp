/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamVBranch.h"

std::vector<GamVBranch *> GamVBranch::fAvailableBranches;

GamVBranch::GamVBranch(std::string vname, char vtype) {
    fBranchName = vname;
    fBranchType = vtype;
}

template<class T>
void GamBranch<T>::FillToRoot(G4GenericAnalysisManager *, unsigned long) {
    std::ostringstream oss;
    oss << "FillToRoot<T> must be implemented " << typeid(T).name();
    Fatal(oss.str());
}

template<>
void GamBranch<double>::FillToRoot(G4GenericAnalysisManager *am, unsigned long i) {
    am->FillNtupleDColumn(fBranchRootId, values[i]);
}

template<>
void GamBranch<std::string>::FillToRoot(G4GenericAnalysisManager *am, unsigned long i) {
    DDD(fBranchName);
    DDD(fBranchType);
    DDD(i);
    DDD(fBranchId);
    DDD(fBranchRootId);
    DDD(values[i]);
    //G4String * s = new G4String;
    am->FillNtupleSColumn(fBranchRootId, values[i]);
}


template<>
void GamBranch<G4ThreeVector>::FillToRoot(G4GenericAnalysisManager *am, unsigned long i) {
    am->FillNtupleDColumn(fBranchRootId, values[i].x());
    am->FillNtupleDColumn(fBranchRootId + 1, values[i].y());
    am->FillNtupleDColumn(fBranchRootId + 2, values[i].z());
}


void GamVBranch::InitAvailableBranches() {
    DDD("InitAvailableBranches");
    // Do nothing if already initialized
    if (!fAvailableBranches.empty()) return;

    DeclareBranch("KineticEnergy", 'D',
                  [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                      auto bv = branch->GetAsDoubleBranch();
                      bv->values.push_back(step->GetPostStepPoint()->GetKineticEnergy());
                  }
    );
    DeclareBranch("TotalEnergyDeposit", 'D',
                  [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                      auto bv = branch->GetAsDoubleBranch();
                      bv->values.push_back(step->GetTotalEnergyDeposit());
                  }
    );
    DeclareBranch("PostPosition", '3',
                  [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                      auto bv = branch->GetAsThreeVectorBranch();
                      bv->values.push_back(step->GetPostStepPoint()->GetPosition());
                  }
    );
    DeclareBranch("LocalTime", 'D',
                  [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                      auto bv = branch->GetAsDoubleBranch();
                      bv->values.push_back(step->GetPostStepPoint()->GetLocalTime());
                  }
    );
    DeclareBranch("VolumeName", 'S',
                  [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                      auto bv = branch->GetAsStringBranch();
                      auto n = step->GetTrack()->GetVolume()->GetName();
                      bv->values.push_back(n);
                  }
    );
}

GamVBranch *GamVBranch::CreateBranch(std::string vname, char vtype, StepFillFunction f) {
    GamVBranch *b = nullptr;
    if (vtype == 'D')
        b = new GamBranch<double>(vname, vtype);
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

GamVBranch *GamVBranch::DeclareBranch(std::string vname, char vtype, StepFillFunction f) {
    // FIXME check type
    auto b = CreateBranch(vname, vtype, f);
    GamVBranch::fAvailableBranches.push_back(b);
    return b;
}

GamBranch<double> *GamVBranch::GetAsDoubleBranch() {
    return dynamic_cast<GamBranch<double> *>(this);
}

GamBranch<G4ThreeVector> *GamVBranch::GetAsThreeVectorBranch() {
    return dynamic_cast<GamBranch<G4ThreeVector> *>(this);
}

GamBranch<std::string> *GamVBranch::GetAsStringBranch() {
    return dynamic_cast<GamBranch<std::string> *>(this);
}

GamVBranch *GamVBranch::CreateBranchCopy() {
    auto b = CreateBranch(fBranchName, fBranchType, fFillStep);
    return b;
}

void GamVBranch::FillStep(G4Step *step, G4TouchableHistory *history) {
    DDD(fBranchName);
    fFillStep(this, step, history);
}

std::string GamVBranch::DumpAvailableBranchesList() {
    std::ostringstream oss;
    for (auto branch:GamVBranch::fAvailableBranches)
        oss << branch->fBranchName << " ";
    return oss.str();
}
