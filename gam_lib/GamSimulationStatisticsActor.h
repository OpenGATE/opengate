/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSimulationStatisticsActor_h
#define GamSimulationStatisticsActor_h

#include <pybind11/stl.h>
#include "G4VAccumulable.hh"
#include "G4Accumulable.hh"
#include "GamVActor.h"
#include "GamHelpers.h"

namespace py = pybind11;

class TrackTypesAccumulable : public G4VAccumulable {
public:
    TrackTypesAccumulable(const G4String &name = "default") : G4VAccumulable(name) {}

    virtual ~TrackTypesAccumulable() {}

    virtual void Merge(const G4VAccumulable &other) {
        DDD("TrackTypesAccumulable Merge");
        const TrackTypesAccumulable &o
                = static_cast<const TrackTypesAccumulable &>(other);
        auto f = o.fTrackTypes;
        for (auto item:f) {
            DDD(item.first);
        }
        DDD("-----")
        for (auto item:fTrackTypes) {
            DDD(item.first);
        }
    }

    virtual void Reset() {
        fTrackTypes.empty();
    }

    py::dict GetValue() {
        py::dict a;
        for (auto item:fTrackTypes) {
            a[py::str(item.first)] = py::int_(item.second);
        }
        return a;
    }

    //py::dict fTrackTypes;
    std::map<std::string, int> fTrackTypes;
};


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

    // Called every time a Track starts (all threads)
    virtual void PreUserTrackingAction(const G4Track *track);

    // Called every time a batch of step must be processed
    virtual void SteppingAction(G4Step *, G4TouchableHistory *);

    py::dict GetCounts() { return fCounts; }

    void SetRunCount(int i) { fRunCount = i; }

    void SetEventCount(int i) { fEventCount = i; }

    void SetTrackCount(int i) { fTrackCount = i; }

    void SetStepCount(int i) { fStepCount = i; }

    G4Accumulable<int> fRunCount;
    G4Accumulable<int> fEventCount;
    G4Accumulable<int> fTrackCount;
    G4Accumulable<int> fStepCount;

    int track_test;

    double fDuration{};
    std::chrono::system_clock::time_point fStartTime;
    std::chrono::system_clock::time_point fStopTime;
    std::chrono::steady_clock::time_point fStartTimeDuration;
    std::chrono::steady_clock::time_point fStopTimeDuration;
    bool fTrackTypesFlag;
    TrackTypesAccumulable fTrackTypes;

protected:
    void CreateCounts();

    py::dict fCounts;
};

#endif // GamSimulationStatisticsActor_h
