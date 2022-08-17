/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef OPENGATE_CORE_OPENGATEHITSENERGYWINDOWSACTOR_H
#define OPENGATE_CORE_OPENGATEHITSENERGYWINDOWSACTOR_H

#include <pybind11/stl.h>
#include "G4Cache.hh"
#include "GateVActor.h"
#include "GateHitsCollection.h"
#include "GateHelpersHits.h"

namespace py = pybind11;

/*
 * Simple actor that use a input Hits Collection and split into several ones
 * with some thresholds on the TotalEnergyDeposit
 */

class GateHitsEnergyWindowsActor : public GateVActor {

public:

    explicit GateHitsEnergyWindowsActor(py::dict &user_info);

    virtual ~GateHitsEnergyWindowsActor();

    // Called when the simulation start (master thread only)
    void StartSimulationAction() override;

    // Called every time a Run starts (all threads)
    void BeginOfRunAction(const G4Run *run) override;

    // Called every time an Event starts
    void BeginOfEventAction(const G4Event *event) override;

    // Called every time a Event ends (all threads)
    void EndOfEventAction(const G4Event *event) override;

    // Called every time a Run ends (all threads)
    void EndOfRunAction(const G4Run *run) override;

    // Called when the simulation end (all threads)
    void EndOfSimulationWorkerAction(const G4Run * /*run*/) override;

    // Called when the simulation end (master thread only)
    void EndSimulationAction() override;

    // Get the id of the last hit energy window
    int GetLastEnergyWindowId();

protected:
    std::string fOutputFilename;
    std::string fInputHitsCollectionName;
    GateHitsCollection *fInputHitsCollection;
    std::vector<std::string> fUserSkipHitAttributeNames;
    std::vector<GateHitsCollection *> fChannelHitsCollections;
    std::vector<std::string> fChannelNames;
    std::vector<double> fChannelMin;
    std::vector<double> fChannelMax;
    int fClearEveryNEvents;

    void ApplyThreshold(size_t i, double min, double max);

    // During computation
    struct threadLocalT {
        std::vector<GateHitsAttributesFiller *> fFillers;
        std::vector<double> *fInputEdep;
        int fLastEnergyWindowId;
    };
    G4Cache<threadLocalT> fThreadLocalData;
};

#endif // OPENGATE_CORE_OPENGATEHITSENERGYWINDOWSACTOR_H
