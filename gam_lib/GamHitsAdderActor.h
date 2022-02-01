/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamHitsAdderActor_h
#define GamHitsAdderActor_h

#include <pybind11/stl.h>
#include "G4Cache.hh"
#include "GamVActor.h"
#include "GamHitsCollection.h"
#include "GamTHitAttribute.h"
#include "GamHitsHelpers.h"

namespace py = pybind11;

/*
 * Create a collection of "singles":
 *
 * - when every event ends, we consider all hits in the attached volume (whatever the sub volumes)
 * - sum all deposited energy
 * - compute one single position, either the one the hit with the max energy (TakeEnergyWinner)
 *   or the energy weighted position (TakeEnergyCentroid)
 *
 *  Warning: if the volume is composed of several sub volumes, this is ignored. All hits are
 *  considered.
 *
 *  Warning: hits are gathered per Event, not per time.
 *
 */

class GamHitsAdderActor : public GamVActor {

public:

    enum AdderPolicy {
        Error, TakeEnergyWinner, TakeEnergyCentroid
    };

    explicit GamHitsAdderActor(py::dict &user_info);

    virtual ~GamHitsAdderActor();

    // Called when the simulation start (master thread only)
    virtual void StartSimulationAction();

    // Called when the simulation end (master thread only)
    virtual void EndSimulationAction();

    // Called every time a Run starts (all threads)
    virtual void BeginOfRunAction(const G4Run *run);

    // Called every time a Run ends (all threads)
    virtual void EndOfRunAction(const G4Run *run);

    void EndOfSimulationWorkerAction(const G4Run *);

    // Called every time a Event starts (all threads)
    virtual void BeginOfEventAction(const G4Event *event);

    // Called every time a Event endss (all threads)
    virtual void EndOfEventAction(const G4Event *event);

protected:
    std::string fOutputFilename;
    std::string fInputHitsCollectionName;
    std::string fOutputHitsCollectionName;
    GamHitsCollection *fOutputHitsCollection;
    GamHitsCollection *fInputHitsCollection;
    AdderPolicy fPolicy;
    std::vector<std::string> fUserSkipHitAttributeNames;

    void InitializeComputation();

    // During computation
    struct threadLocalT {
        std::vector<double> *fInputEdep;
        std::vector<G4ThreeVector> *fInputPos;
        GamHitsAttributesFiller *fHitsAttributeFiller;
        GamVHitAttribute *fOutputEdepAttribute;
        GamVHitAttribute *fOutputPosAttribute;
        size_t fIndex;
    };
    G4Cache<threadLocalT> fThreadLocalData;

};

#endif // GamHitsAdderActor_h
