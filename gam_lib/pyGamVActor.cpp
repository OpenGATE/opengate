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

class PyGamVActor : public GamVActor {
public:
    // Inherit the constructors
    using GamVActor::GamVActor;

    void SteppingAction(G4Step *step,
                        G4TouchableHistory *touchable) override {
        PYBIND11_OVERLOAD(void, GamVActor, SteppingAction, step, touchable);
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
            .def(py::init<std::string>())
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

