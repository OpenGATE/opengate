/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSimulationStatisticsActor_h
#define GamSimulationStatisticsActor_h

#include <pybind11/stl.h>
#include "GamVActor.h"
#include "GamHelpers.h"

namespace py = pybind11;

class GamSimulationStatisticsActor : public GamVActor {

public:

    //explicit GamSimulationStatisticsActor(std::string type_name);
    explicit GamSimulationStatisticsActor(py::dict &user_info);

    virtual ~GamSimulationStatisticsActor();

    // Called when the simulation start (master thread only)
    virtual void StartSimulationAction();

    // Called when the simulation end (master thread only)
    virtual void EndSimulationAction();

    // Called every time a Run starts (all threads)
    virtual void BeginOfRunAction(const G4Run *run);

    // Called every time a Run ends (all threads)
    virtual void EndOfRunAction(const G4Run *run);

    // Called every time the simulation is about to end (all threads)
    virtual void EndOfSimulationWorkerAction(const G4Run *lastRun);

    // Called every time a Track starts (all threads)
    virtual void PreUserTrackingAction(const G4Track *track);

    // Called every time a batch of step must be processed
    virtual void SteppingAction(G4Step *, G4TouchableHistory *);

    py::dict GetCounts();

protected:

    // Local data for the threads (each one has a copy)
    struct threadLocal_t {
        int fRunCount;
        int fEventCount;
        long int fTrackCount;
        long int fStepCount;
        std::map<std::string, long int> fTrackTypes;
    };
    G4Cache<threadLocal_t> threadLocalData;

    // fCounts will contain the final dictionary of all data,
    std::map<std::string, long int> fCounts;
    std::map<std::string, double> fCountsD;
    std::map<std::string, std::string> fCountsStr;


    bool fTrackTypesFlag;
    std::map<std::string, long int> fTrackTypes;
    double fDuration;
    double fInitDuration;
    std::chrono::system_clock::time_point fStartTime;
    std::chrono::system_clock::time_point fStartRunTime;
    std::chrono::system_clock::time_point fStopTime;
    bool fStartRunTimeIsSet;
};

#endif // GamSimulationStatisticsActor_h
