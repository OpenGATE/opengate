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
#include "G4RootAnalysisManager.hh"
#include "GamVActor.h"
#include "GamHelpers.h"

template<class T>
class GamBranch;

class GamVBranch;

class BranchFillStep {
public:
    virtual void FillStep(GamVBranch *b, G4Step *, G4TouchableHistory *);
};


class GamVBranch {
public:
    GamVBranch(std::string vname, char vtype);

    virtual ~GamVBranch();

    typedef std::function<void(GamVBranch *b, G4Step *, G4TouchableHistory *)> StepFillFunction;

    std::string fBranchName;
    char fBranchType;
    StepFillFunction fFillStep;
    unsigned long fBranchId;
    unsigned long fBranchRootId; // temporary used when WriteToRoot // FIXME

    void FillStep(G4Step *, G4TouchableHistory *);

    virtual GamVBranch *CreateBranchCopy();

    GamBranch<double> *GetAsDoubleBranch();

    GamBranch<int> *GetAsIntBranch();

    GamBranch<G4ThreeVector> *GetAsThreeVectorBranch();

    GamBranch<std::string> *GetAsStringBranch();

    std::vector<double> & GetValuesAsDouble();

    void push_back_double(double d);

    void push_back_int(int d);

    virtual void CopyValues(GamVBranch *output, std::vector<unsigned long> &indexes) = 0;

    //virtual void FillToRoot(G4GenericAnalysisManager *am, unsigned long i) = 0;
    virtual void FillToRoot(G4RootAnalysisManager *am, unsigned long i) = 0;

    virtual unsigned long size() = 0;

    /// --------------------------------------------
    /// Below are static elements to manage branches

    // Can be used for cpp stepFillFunction or py StepFillFunction
    static GamVBranch *DefineBranch(std::string vname, char vtype, const StepFillFunction &f);

    static void InitAvailableBranches();

    static std::vector<GamVBranch *> fAvailableBranches;

    static std::vector<GamVBranch *> &GetAvailableBranches() { return fAvailableBranches; }
    //static GamVBranch **GetAvailableBranches() { return fAvailableBranches; }

    static std::string DumpAvailableBranchesList();

    static void FreeAvailableBranches();

protected:
    static GamVBranch *CreateBranch(std::string vname, char vtype, const StepFillFunction &f);


};

#endif // GamVBranch_h
