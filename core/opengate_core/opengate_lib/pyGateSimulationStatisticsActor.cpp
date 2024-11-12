/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateSimulationStatisticsActor.h"

/*

 // It is possible to have access to Run/Event/Track/Step from python side
 // by using below "trampoline functions".
 // It is however slow, so probably only useful for prototype or special cases.

//
https://pybind11.readthedocs.io/en/stable/advanced/classes.html#virtual-and-inheritance

class PyGateSimulationStatisticsActor : public GateSimulationStatisticsActor {
public:
    // Inherit the constructors
    using GateSimulationStatisticsActor::GateSimulationStatisticsActor;

    void SteppingAction(G4Step *step,
                        G4TouchableHistory *touchable) override {
        PYBIND11_OVERLOAD(void, GateSimulationStatisticsActor, SteppingAction,
step, touchable);
    }

    void BeginOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GateSimulationStatisticsActor, BeginOfRunAction,
Run);
    }

    void EndOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GateSimulationStatisticsActor, EndOfRunAction,
Run);
    }

    void BeginOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GateSimulationStatisticsActor,
BeginOfEventAction, event);
    }

    void EndOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GateSimulationStatisticsActor, EndOfEventAction,
event);
    }


    void PreUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GateSimulationStatisticsActor,
PreUserTrackingAction, track);
    }

    void PostUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GateSimulationStatisticsActor,
PostUserTrackingAction, track);
    }

};
*/

void init_GateSimulationStatisticsActor(py::module &m) {

  py::class_<GateSimulationStatisticsActor, // PyGateSimulationStatisticsActor,
             std::unique_ptr<GateSimulationStatisticsActor, py::nodelete>,
             GateVActor>(m, "GateSimulationStatisticsActor")
      .def(py::init<py::dict &>())
      .def("InitializeUserInfo",
           &GateSimulationStatisticsActor::InitializeUserInfo)
      .def("GetCounts", &GateSimulationStatisticsActor::GetCounts);
}
