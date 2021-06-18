/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamHitsCollectionActor_h
#define GamHitsCollectionActor_h

#include <pybind11/stl.h>

#if defined(__clang__)
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wshadow"
#endif

//#include "TROOT.h"
#include "TFile.h"
#include "TTree.h"

#if defined(__clang__)
#pragma clang diagnostic pop
#endif


#include "G4GenericAnalysisManager.hh"
#include "G4RootAnalysisManager.hh"
#include "G4Cache.hh"
#include "GamVActor.h"
#include "GamHelpers.h"
#include "GamBranches.h"

namespace py = pybind11;


class GamVBranch {
public:
    std::string name;
    char type;

    virtual void FillStep(G4Step *step, G4TouchableHistory *touchable) = 0;
};

template<class T>
class GamBranch : public GamVBranch {
public:
    std::vector<T> values;
};

class GamKineticEnergyBranch : public GamBranch<double> {
public:
    GamKineticEnergyBranch() {
        name = "KineticEnergy";
        type = 'D';
    }

    virtual void FillStep(G4Step *step, G4TouchableHistory *touchable) {
        values.push_back(step->GetPostStepPoint()->GetKineticEnergy());
    }
};

class GamHitsCollectionActor : public GamVActor {

public:

    //explicit GamHitsCollectionActor(std::string type_name);
    explicit GamHitsCollectionActor(py::dict &user_info);

    virtual ~GamHitsCollectionActor();

    // Called when the simulation start (master thread only)
    virtual void StartSimulationAction();

    // Called when the simulation end (master thread only)
    virtual void EndSimulationAction();

    // Called every time a Run starts (all threads)
    virtual void BeginOfRunAction(const G4Run *run);

    // Called every time a Run ends (all threads)
    virtual void EndOfRunAction(const G4Run *run);

    // Called every time a Event starts (all threads)
    virtual void BeginOfEventAction(const G4Event *event);

    virtual void EndOfEventAction(const G4Event *event);

    // Called every time a Track starts (all threads)
    virtual void PreUserTrackingAction(const G4Track *track);

    // Called every time a batch of step must be processed
    virtual void SteppingAction(G4Step *, G4TouchableHistory *);

    std::vector<std::string> fStepFillNames;

protected:
    void BuildAvailableElements();

    std::vector<GamBranches::BranchFillStepStruct> fStepSelectedBranches;
    std::string fOutputFilename;
    G4RootAnalysisManager *fAnalysisManager;

    TFile *fTFile;
    TTree fTree;

    int fPreviousIndex;

    struct BranchRootStruct;
    typedef std::function<void(TTree &tree,
                               BranchRootStruct &,
                               G4Step *,
                               G4TouchableHistory *)> StepRootFillFunction;

    typedef struct BranchRootStruct { // FIXME as a class template on dvalue
        std::string name;
        char type;
        Double_t dvalue;
        StepRootFillFunction fill;
    };

    std::vector<BranchRootStruct> fRootBranches;

    std::vector<GamVBranch *> fBranches;

};

#endif // GamHitsCollectionActor_h
