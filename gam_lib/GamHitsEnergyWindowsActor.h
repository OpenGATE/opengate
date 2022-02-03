/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GAM_G4_GAMHITSENERGYWINDOWSACTOR_H
#define GAM_G4_GAMHITSENERGYWINDOWSACTOR_H

#include <pybind11/stl.h>
#include "G4Cache.hh"
#include "GamVActor.h"
#include "GamHitsCollection.h"
#include "GamHitsHelpers.h"

namespace py = pybind11;

/*
 * Simple actor that use a input Hits Collection and split into several ones
 * with some thresholds on the TotalEnergyDeposit
 */

class GamHitsEnergyWindowsActor : public GamVActor {

public:

    explicit GamHitsEnergyWindowsActor(py::dict &user_info);

    virtual ~GamHitsEnergyWindowsActor();

    // Called when the simulation start (master thread only)
    virtual void StartSimulationAction();

    // Called when the simulation end (master thread only)
    virtual void EndSimulationAction();

    // Called every time a Run starts (all threads)
    virtual void BeginOfRunAction(const G4Run *run);

    // Called every time a Run ends (all threads)
    virtual void EndOfRunAction(const G4Run *run);

    void EndOfSimulationWorkerAction(const G4Run *);

    // Called every time a Event endss (all threads)
    virtual void EndOfEventAction(const G4Event *event);

protected:
    std::string fOutputFilename;
    std::string fInputHitsCollectionName;
    GamHitsCollection *fInputHitsCollection;
    std::vector<std::string> fUserSkipHitAttributeNames;
    std::vector<GamHitsCollection *> fChannelHitsCollections;
    std::vector<std::string> fChannelNames;
    std::vector<double> fChannelMin;
    std::vector<double> fChannelMax;

    void ApplyThreshold(size_t i, double min, double max);

    // During computation
    struct threadLocalT {
        std::vector<GamHitsAttributesFiller *> fFillers;
        std::vector<double> *fInputEdep;
        size_t fIndex;
    };
    G4Cache<threadLocalT> fThreadLocalData;
};

#endif // GAM_G4_GAMHITSENERGYWINDOWSACTOR_H
