/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamPhaseSpaceActor2_h
#define GamPhaseSpaceActor2_h

#include <pybind11/stl.h>
#include "G4GenericAnalysisManager.hh"
#include "G4Cache.hh"
#include "GamVActor.h"
#include "GamHelpers.h"
#include "GamHitsCollection.h"

namespace py = pybind11;

class GamPhaseSpaceActor2 : public GamVActor {

public:

    //explicit GamPhaseSpaceActor2(std::string type_name);
    explicit GamPhaseSpaceActor2(py::dict &user_info);

    virtual ~GamPhaseSpaceActor2();

    // Called when the simulation start (master thread only)
    void StartSimulationAction() override;

    // Called every time a Run starts (all threads)
    void BeginOfRunAction(const G4Run *run) override;

    // Called every time a Event starts (all threads)
    void BeginOfEventAction(const G4Event *event) override;

    // Called every time a Track starts (all threads)
    void PreUserTrackingAction(const G4Track *track) override;

    // Called every time a batch of step must be processed
    void SteppingAction(G4Step *, G4TouchableHistory *) override;

    // Called every time a Run ends (all threads)
    void EndOfRunAction(const G4Run *run) override;

    void EndOfSimulationWorkerAction(const G4Run *run) override;

    // Called when the simulation end (master thread only)
    void EndSimulationAction() override;

protected:

    // Local data for the threads (each one has a copy)
    struct threadLocalT {
        bool currentTrackAlreadyStored;
    };
    G4Cache<threadLocalT> fThreadLocalData;

    std::string fOutputFilename;
    std::string fHitsCollectionName;
    std::vector<std::string> fUserHitAttributeNames;
    GamHitsCollection *fHits;

};

#endif // GamPhaseSpaceActor2_h
