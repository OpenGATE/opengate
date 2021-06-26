/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamVBranch_h
#define GamVBranch_h

#include <pybind11/stl.h>

#include "GamVActor.h"
#include "GamHelpers.h"
#include "GamBranches.h"

namespace py = pybind11;

template<class T>
class GamBranch;

class GamVBranch {
public:
    GamVBranch(std::string vname, char vtype);

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

    /// Below are static elements to manage branches

    static GamVBranch *CreateBranch(std::string vname, char vtype, StepFillFunction f);

    static GamVBranch *DeclareBranch(std::string vname, char vtype, StepFillFunction f);

    static void InitAvailableBranches();

    static std::vector<GamVBranch *> fAvailableBranches;

    static std::string DumpAvailableBranchesList();

};


template<class T>
class GamBranch : public GamVBranch {
public:
    GamBranch(std::string vname, char vtype) : GamVBranch(vname, vtype) {}

    virtual void CopyValues(GamVBranch *output, std::vector<unsigned long> &indexes);

    virtual void FillToRoot(G4GenericAnalysisManager *am, unsigned long i);

    virtual unsigned long size() { return values.size(); }

    std::vector<T> values;

};

template<class T>
void GamBranch<T>::CopyValues(GamVBranch *output, std::vector<unsigned long> &indexes) {
    DDD("CopyValues");
    DDD(fBranchName);
    DDD(fBranchType);
    DDD(fBranchId);
    DDD(values.size());
    DDD(output->fBranchName);
    auto voutput = dynamic_cast<GamBranch<T> *>(output);
    DDD(voutput->fBranchName);
    DDD(voutput->values.size());
    DDD(voutput->fBranchType);
    DDD(voutput->fBranchId);
    for (auto i = 0; i < indexes.size(); i++) {
        DDD(indexes[i]);
        DDD(values[indexes[i]]);
        voutput->values.push_back(values[indexes[i]]);
    }
    DDD("end");
}

#endif // GamVBranch_h
