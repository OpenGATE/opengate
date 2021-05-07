/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamVActor.h"
#include "GamHelpers.h"

/*
 * The "trampoline" functions below are required if we want to
 * allow callbacks on the py side.
 *
 * If it is not needed: to not define trampoline functions in class that inherit from VActor.
 *
 * It must be defined also in all classes that inherit from GamVActor
 *
 * Hence, BeginOfRunAction, BeginOfEventAction etc maybe define in py side
 * (but it will be slower, especially for steps)
 */

class PyGamVActor : public GamVActor {
public:
    // Inherit the constructors
    using GamVActor::GamVActor;

    void SteppingAction(G4Step *step,
                        G4TouchableHistory *touchable) override {
        PYBIND11_OVERLOAD(void, GamVActor, SteppingAction, step, touchable);
    }

    void BeginOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamVActor, BeginOfRunAction, Run);
    }

    void EndOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamVActor, EndOfRunAction, Run);
    }

    void BeginOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamVActor, BeginOfEventAction, event);
    }

    void EndOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamVActor, EndOfEventAction, event);
    }

    void PreUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamVActor, PreUserTrackingAction, track);
    }

    void PostUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamVActor, PostUserTrackingAction, track);
    }

};

void init_GamVActor(py::module &m) {

    py::class_<GamVActor, PyGamVActor,
        std::unique_ptr<GamVActor, py::nodelete>>(m, "GamVActor")
        .def(py::init<py::dict &>())
        .def("RegisterSD", &GamVActor::RegisterSD)
        .def_readwrite("fActions", &GamVActor::fActions)
        .def("ActorInitialize", &GamVActor::ActorInitialize)

        .def("StartSimulationAction", &GamVActor::StartSimulationAction)
        .def("EndSimulationAction", &GamVActor::EndSimulationAction)
        .def("BeginOfRunAction", &GamVActor::BeginOfRunAction)
        .def("EndOfRunAction", &GamVActor::EndOfRunAction)
        .def("BeginOfEventAction", &GamVActor::BeginOfEventAction)
        .def("EndOfEventAction", &GamVActor::EndOfEventAction)
        .def("PreUserTrackingAction", &GamVActor::PreUserTrackingAction)
        .def("PostUserTrackingAction", &GamVActor::PostUserTrackingAction)
        .def("SteppingAction", &GamVActor::SteppingAction);
}

