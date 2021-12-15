/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamTree_h
#define GamTree_h

#include <pybind11/stl.h>
#include "GamVActor.h"
#include "GamHelpers.h"
#include "GamTBranch.h"
#include "G4VHit.hh"
#include "G4AttDef.hh"
#include "G4AttValue.hh"

class GamTree {
public:
    GamTree(std::string vname);

    virtual ~GamTree();

    std::string fTreeName = "Tree";
    std::vector<GamVBranch *> fBranches;
    std::map<std::string, GamVBranch *> fBranchesMap;

    void AddBranch(std::string vname);

    void FillStep(G4Step *step, G4TouchableHistory *touchable);

    GamVBranch *GetBranch(std::string vname);

    GamBranch<double> *GetDoubleBranch(std::string vname);

    GamBranch<G4ThreeVector> *GetThreeVectorBranch(std::string vname);

    GamBranch<std::string> *GetStringBranch(std::string vname);

    std::string Dump();

    void FreeBranches();

    tools::wroot::ntuple* GetNTuple();


        // To root (via G4?)
    void WriteToRoot(std::string filename);

};

#endif // GamTree_h
