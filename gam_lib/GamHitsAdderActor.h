/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSinglesCollectionActor_h
#define GamSinglesCollectionActor_h

#include <pybind11/stl.h>
#include "GamVActor.h"
#include "GamHitsCollection.h"

namespace py = pybind11;

/*
 * Create a collection of singles:
 *
 * - every event, consider all hits in the attached volume (whatever the sub volumes)
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

    enum AdderPolicy {Error, TakeEnergyWinner, TakeEnergyCentroid};

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

    // Called every time a Event starts (all threads)
    virtual void BeginOfEventAction(const G4Event *event);

    // Called every time a Event endss (all threads)
    virtual void EndOfEventAction(const G4Event *event);

protected:
    std::string fOutputFilename;
    std::string fInputHitsCollectionName;
    std::string fOutputHitsCollectionName;
    GamHitsCollection * fOutputHitsCollection;
    GamHitsCollection * fInputHitsCollection;
    AdderPolicy fPolicy;

    // During computation
    size_t fIndex;

};

#endif // GamSinglesCollectionActor_h
