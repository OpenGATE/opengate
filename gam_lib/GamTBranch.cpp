/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamTBranch.h"

template<>
void GamBranch<double>::FillToRoot(G4GenericAnalysisManager *am, unsigned long i) {
    am->FillNtupleDColumn(fBranchRootId, values[i]);
}

template<>
void GamBranch<std::string>::FillToRoot(G4GenericAnalysisManager *am, unsigned long i) {
    am->FillNtupleSColumn(fBranchRootId, values[i]);
}


template<>
void GamBranch<G4ThreeVector>::FillToRoot(G4GenericAnalysisManager *am, unsigned long i) {
    am->FillNtupleDColumn(fBranchRootId, values[i].x());
    am->FillNtupleDColumn(fBranchRootId + 1, values[i].y());
    am->FillNtupleDColumn(fBranchRootId + 2, values[i].z());
}

