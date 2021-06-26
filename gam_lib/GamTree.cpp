/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4GenericAnalysisManager.hh"
#include "GamTree.h"

void GamTree::AddBranch(std::string vname) {
    for (auto branch:GamVBranch::fAvailableBranches) {
        if (branch->fBranchName == vname) {
            auto b = branch->CreateBranchCopy();
            fBranches.push_back(b);
            DDD(vname);
            b->fBranchId = fBranches.size() - 1;
            DDD(b->fBranchId);
            fBranchesMap[vname] = b;
            return;
        }
    }
    std::ostringstream oss;
    oss << "Cannot find a branch name '" << vname
        << "' in the list of available branches ("
        << GamVBranch::fAvailableBranches.size() << ") "
        << GamVBranch::DumpAvailableBranchesList();
    Fatal(oss.str());
}

void GamTree::FillStep(G4Step *step, G4TouchableHistory *history) {
    for (auto branch:fBranches)
        branch->FillStep(step, history);
}

GamVBranch *GamTree::GetBranch(std::string vname) {
    // FIXME check exist
    return fBranchesMap[vname];
}

GamBranch<G4ThreeVector> *GamTree::GetThreeVectorBranch(std::string vname) {
    return GetBranch(std::move(vname))->GetAsThreeVectorBranch();
}

GamBranch<double> *GamTree::GetDoubleBranch(std::string vname) {
    return GetBranch(vname)->GetAsDoubleBranch();
}

void GamTree::WriteToRoot(std::string filename) {
    DDD(filename);
    auto fAnalysisManager = G4GenericAnalysisManager::Instance();
    fAnalysisManager->OpenFile(filename);
    //fAnalysisManager->SetNtupleMerging(true);
    DDD(name);
    fAnalysisManager->CreateNtuple(name, "Hits collection");
    int i = 0;
    for (auto b:fBranches) {
        b->fBranchRootId = i;
        DDD(b->fBranchName);
        DDD(b->fBranchId);
        DDD(b->fBranchRootId);
        DDD(b->fBranchType);
        if (b->fBranchType == 'D') fAnalysisManager->CreateNtupleDColumn(b->fBranchName);
        if (b->fBranchType == 'S') {
            DDD("here S");
            fAnalysisManager->CreateNtupleSColumn(b->fBranchName);
        }
        if (b->fBranchType == 'I') fAnalysisManager->CreateNtupleIColumn(b->fBranchName);
        if (b->fBranchType == '3') {
            fAnalysisManager->CreateNtupleDColumn(b->fBranchName + "_X");
            fAnalysisManager->CreateNtupleDColumn(b->fBranchName + "_Y");
            fAnalysisManager->CreateNtupleDColumn(b->fBranchName + "_Z");
            // FIXME
            i += 2;
        }
        i++;
    }
    DDD("la");
    DDD(fAnalysisManager->GetNofNtuples());
    for (auto i = 0; i < fAnalysisManager->GetNofNtuples(); i++) {
        //auto t= fAnalysisManager->GetNtuple(i);
    }
    //DDD(i);
    fAnalysisManager->FinishNtuple();
    for (unsigned long j = 0; j < fBranches[0]->size(); j++) {
        for (auto b:fBranches) {
            b->FillToRoot(fAnalysisManager, j);
        }
        fAnalysisManager->AddNtupleRow();
    }
    DDD("after");
    fAnalysisManager->Write();
    fAnalysisManager->CloseFile(); // not really needed ?
}

std::string GamTree::Dump() {
    std::ostringstream oss;
    oss << "Tree: " << name << " " << fBranches.size() << " branches: ";
    for (auto b:fBranches) {
        oss << b->fBranchName << " (" << b->fBranchType << " " << b->size() << ") ";
    }
    return oss.str();
}
