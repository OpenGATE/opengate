/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamHitsCollectionActor_h
#define GamHitsCollectionActor_h

#include <pybind11/stl.h>
#include "GamVActor.h"
#include "GamHitsCollection.h"

namespace py = pybind11;

class GamHitsCollectionActor : public GamVActor {

public:

    explicit GamHitsCollectionActor(py::dict &user_info);

    virtual ~GamHitsCollectionActor();

    // Called when the simulation start (master thread only)
    void StartSimulationAction() override;

    // Called every time a Run starts (all threads)
    void BeginOfRunAction(const G4Run *run) override;

    // Called every time a batch of step must be processed
    void SteppingAction(G4Step * /*unused*/) override;

    // Called every time a Run ends (all threads)
    void EndOfRunAction(const G4Run *run) override;

    // Called by every worker when the simulation is about to end
    void EndOfSimulationWorkerAction(const G4Run * /*lastRun*/) override;

    // Called when the simulation end (master thread only)
    void EndSimulationAction() override;


protected:
    std::string fOutputFilename;
    std::string fHitsCollectionName;
    std::vector<std::string> fUserHitAttributeNames;
    GamHitsCollection *fHits;
    bool fDebug;

};

#endif // GamHitsCollectionActor_h
