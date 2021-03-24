/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamSimulationStatisticsActor.h"

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html#virtual-and-inheritance

class PyGamSimulationStatisticsActor : public GamSimulationStatisticsActor {
public:
    // Inherit the constructors
    using GamSimulationStatisticsActor::GamSimulationStatisticsActor;

    void SteppingAction(G4Step *step,
                        G4TouchableHistory *touchable) override {
        PYBIND11_OVERLOAD(void, GamSimulationStatisticsActor, SteppingAction, step, touchable);
    }

    void BeginOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamSimulationStatisticsActor, BeginOfRunAction, Run);
    }

    void EndOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamSimulationStatisticsActor, EndOfRunAction, Run);
    }

    void BeginOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamSimulationStatisticsActor, BeginOfEventAction, event);
    }

    void EndOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamSimulationStatisticsActor, EndOfEventAction, event);
    }

    void PreUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamSimulationStatisticsActor, PreUserTrackingAction, track);
    }

    void PostUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamSimulationStatisticsActor, PostUserTrackingAction, track);
    }

};

void init_GamSimulationStatisticsActor(py::module &m) {

    py::class_<GamSimulationStatisticsActor, PyGamSimulationStatisticsActor,
            std::unique_ptr<GamSimulationStatisticsActor, py::nodelete>,
            GamVActor>(m, "GamSimulationStatisticsActor")
            .def(py::init<py::dict &>())

            .def("BeginOfRunAction", &GamVActor::BeginOfRunAction)
            .def("EndOfRunAction", &GamVActor::EndOfRunAction)

            .def("GetCounts", &GamSimulationStatisticsActor::GetCounts)

            .def("SetRunCount", &GamSimulationStatisticsActor::SetRunCount)
            .def("SetEventCount", &GamSimulationStatisticsActor::SetEventCount)
            .def("SetTrackCount", &GamSimulationStatisticsActor::SetTrackCount)
            .def("SetStepCount", &GamSimulationStatisticsActor::SetStepCount);
}

