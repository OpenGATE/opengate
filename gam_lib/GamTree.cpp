/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4GenericAnalysisManager.hh"
#include "G4RootAnalysisManager.hh"
#include "GamTree.h"

GamTree::GamTree(std::string name) {
    fTreeName = name;
}

GamTree::~GamTree() {
}


void GamTree::AddBranch(std::string vname) {
    for (auto branch:GamVBranch::fAvailableBranches) {
        if (branch->fBranchName == vname) {
            auto b = branch->CreateBranchCopy();
            fBranches.push_back(b);
            b->fBranchId = fBranches.size() - 1;
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

GamBranch<std::string> *GamTree::GetStringBranch(std::string vname) {
    return GetBranch(vname)->GetAsStringBranch();
}

void GamTree::WriteToRoot(std::string filename) {
    auto n = fBranches[0]->size();
    if (n == 0) {
        std::cout << "WARNING no branch in tree: " << filename << std::endl;
        return;
    }
    DDD("Write to root");
    //auto fAnalysisManager = G4GenericAnalysisManager::Instance();
    auto fAnalysisManager = G4RootAnalysisManager::Instance();
    fAnalysisManager->OpenFile(filename);
    auto FirstTupleId = fAnalysisManager->CreateNtuple(fTreeName, "Hits collection");
    int i = 0;
    for (auto &b:fBranches) {
        if (b->size() != n) {
            Fatal("Error branches does not have the same size " + fTreeName + " " + b->fBranchName);
        }
        b->fBranchRootId = i;
        if (b->fBranchType == 'D')
            fAnalysisManager->CreateNtupleDColumn(FirstTupleId, b->fBranchName); //FIXME get col ID instead
        if (b->fBranchType == 'S') fAnalysisManager->CreateNtupleSColumn(FirstTupleId, b->fBranchName);
        if (b->fBranchType == 'I') fAnalysisManager->CreateNtupleIColumn(FirstTupleId, b->fBranchName);
        if (b->fBranchType == '3') {
            fAnalysisManager->CreateNtupleDColumn(FirstTupleId, b->fBranchName + "_X");
            fAnalysisManager->CreateNtupleDColumn(FirstTupleId, b->fBranchName + "_Y");
            fAnalysisManager->CreateNtupleDColumn(FirstTupleId, b->fBranchName + "_Z");
            i += 2;
        }
        i++;
    }
    fAnalysisManager->FinishNtuple(FirstTupleId);
    DDD(FirstTupleId);


    auto SecondTupleId = fAnalysisManager->CreateNtuple("Hits2", "Hits collection 2");
    DDD(SecondTupleId);
    auto colID1 = fAnalysisManager->CreateNtupleDColumn(SecondTupleId, "Bidon");
    auto colID2 = fAnalysisManager->CreateNtupleDColumn(SecondTupleId, "AnotherOne");
    fAnalysisManager->FinishNtuple(SecondTupleId);
    DDD(colID1);
    DDD(colID2);

    //for (auto &b:fHitAttributes) b->fBranchRootId = FirstTupleId; // FIXME
    DDD(fAnalysisManager->GetNofNtuples());


    // FIXME Check size of all branches
    auto h = fBranches[0]->size() / 2;
    DDD(h);
    for (unsigned long j = 0; j < fBranches[0]->size(); j++) {
        for (auto &b:fBranches) {
            b->FillToRoot(fAnalysisManager, j);
        }
        fAnalysisManager->AddNtupleRow(FirstTupleId);
        if (i>h) {
            DDD("write");
            fAnalysisManager->Write();
            DDD("done");
        }
        h = fBranches[0]->size();
    }

    // Test second branch
    for (int i = 0; i < 100; i++) {
        //DDD(i);
        fAnalysisManager->FillNtupleDColumn(SecondTupleId, colID1, 666 + i);
        fAnalysisManager->FillNtupleDColumn(SecondTupleId, colID2, 555 - i);
        fAnalysisManager->AddNtupleRow(SecondTupleId);
    }

    DDD(fAnalysisManager->GetNtupleActivation(0));
    DDD(fAnalysisManager->GetNtupleActivation(1));
    DDD(fAnalysisManager->GetFirstNtupleId());
    DDD(fAnalysisManager->GetFirstNtupleColumnId());

    // Now test to access (during runtime)
    for (auto iter = fAnalysisManager->BeginNtuple(); iter != fAnalysisManager->EndNtuple(); iter++) {
        auto hits = *iter;
        hits->print_columns(std::cout);
    }


    fAnalysisManager->Write();
    //fAnalysisManager->CloseFile();
    //delete fAnalysisManager; // important to allow several successive write // FIXME
}

tools::wroot::ntuple *GamTree::GetNTuple() {
    DDD("Get NTuple");
    auto fAnalysisManager = G4RootAnalysisManager::Instance();
    return fAnalysisManager->GetNtuple(0);
    DDD("Get NTuple end ");
}

std::string GamTree::Dump() { // FIXME may be on py side (?)
    std::ostringstream oss;
    oss << "Tree: " << fTreeName << " " << fBranches.size() << " branches: ";
    for (auto b:fBranches) {
        oss << b->fBranchName << " (" << b->fBranchType << " " << b->size() << ") ";
    }
    return oss.str();
}


void GamTree::FreeBranches() {
    for (auto branch:fBranches) {
        //std::cout << "deleting " << branch->fHitAttributeName << " " << std::endl;
        delete branch;
    }
}
