/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamPhaseSpaceActor_h
#define GamPhaseSpaceActor_h

#include <pybind11/stl.h>
#include "G4GenericAnalysisManager.hh"
#include "G4Cache.hh"
#include "GamVActor.h"
#include "GamHelpers.h"
#include "GamBranches.h"

namespace py = pybind11;

class GamPhaseSpaceActor : public GamVActor {

public:

    //explicit GamPhaseSpaceActor(std::string type_name);
    explicit GamPhaseSpaceActor(py::dict &user_info);

    virtual ~GamPhaseSpaceActor();

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

    // Called every time a Track starts (all threads)
    virtual void PreUserTrackingAction(const G4Track *track);

    // Called every time a batch of step must be processed
    virtual void SteppingAction(G4Step *, G4TouchableHistory *);

    std::vector<std::string> fStepFillNames;

protected:

    std::vector<GamBranches::BranchFillStepStruct> fStepSelectedBranches;
    //std::vector<BranchFillStepStruct> fAllBranches;
    std::string fOutputFilename;
    G4GenericAnalysisManager *fAnalysisManager;

    // FIXME replace by thread specific
    std::vector<double> fBeginOfEventTimePerThread;

};

#endif // GamPhaseSpaceActor_h
