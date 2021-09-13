/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamVBranch_h
#define GamVBranch_h

#include <pybind11/stl.h>
#include "G4GenericAnalysisManager.hh"
#include "GamVActor.h"
#include "GamHelpers.h"

template<class T>
class GamBranch;

class GamVBranch {
public:
    GamVBranch(std::string vname, char vtype);

    virtual ~GamVBranch() {}

    typedef std::function<void(GamVBranch *b, G4Step *, G4TouchableHistory *)> StepFillFunction;

    std::string fBranchName;
    char fBranchType;
    StepFillFunction fFillStep;
    unsigned long fBranchId;
    unsigned long fBranchRootId; // temporary used when WriteToRoot

    void FillStep(G4Step *, G4TouchableHistory *);

    virtual GamVBranch *CreateBranchCopy();

    GamBranch<double> *GetAsDoubleBranch();

    GamBranch<G4ThreeVector> *GetAsThreeVectorBranch();

    GamBranch<std::string> *GetAsStringBranch();

    virtual void CopyValues(GamVBranch *output, std::vector<unsigned long> &indexes) = 0;

    virtual void FillToRoot(G4GenericAnalysisManager *am, unsigned long i) = 0;

    virtual unsigned long size() = 0;

    /// --------------------------------------------
    /// Below are static elements to manage branches

    static GamVBranch *CreateBranch(std::string vname, char vtype, StepFillFunction f);

    static GamVBranch *DeclareBranch(std::string vname, char vtype, StepFillFunction f);

    static void InitAvailableBranches();

    static std::vector<GamVBranch *> fAvailableBranches;

    static std::vector<GamVBranch *> & GetAvailableBranches() { return fAvailableBranches; }

    static std::string DumpAvailableBranchesList();

};

#endif // GamVBranch_h
