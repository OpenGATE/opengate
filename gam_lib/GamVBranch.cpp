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

GamBranch<double> *GamVBranch::GetAsDoubleBranch() {
    return static_cast<GamBranch<double> *>(this);
}

GamBranch<G4ThreeVector> *GamVBranch::GetAsThreeVectorBranch() {
    return static_cast<GamBranch<G4ThreeVector> *>(this);
}

GamBranch<std::string> *GamVBranch::GetAsStringBranch() {
    return static_cast<GamBranch<std::string> *>(this);
}


void GamVBranch::InitAvailableBranches() {
    // Do nothing if already initialized
    if (!fAvailableBranches.empty()) return;

    /*
     * Try to keep Geant4 names as much as possible
     */

    DeclareBranch("KineticEnergy", 'D',
                  [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                      // FIXME change to push_back_double ?
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
    DeclareBranch("GlobalTime", 'D',
                  [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                      auto bv = branch->GetAsDoubleBranch();
                      bv->values.push_back(step->GetPostStepPoint()->GetGlobalTime());
                  }
    );
    DeclareBranch("ProperTime", 'D',
                  [=](GamVBranch *branch, G4Step *step, G4TouchableHistory *) {
                      auto bv = branch->GetAsDoubleBranch();
                      bv->values.push_back(step->GetPostStepPoint()->GetProperTime());
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
