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
#include "G4VPrimitiveScorer.hh"

class PyGamVActor : public GamVActor {
public:
    /* Inherit the constructors */
    using GamVActor::GamVActor;

    // Main function to be (optionally) overridden on the py side
    // Will be called every time a batch of step should be processed
    void ProcessHitsPerBatch(bool force = false) override {
        PYBIND11_OVERLOAD(void, GamVActor, ProcessHitsPerBatch, force);
    }

    void SteppingBatchAction() override {
        PYBIND11_OVERLOAD(void, GamVActor, SteppingBatchAction,);
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

    py::class_<GamVActor, PyGamVActor>(m, "GamVActor")
        .def(py::init<std::string>())
        .def("RegisterSD", &GamVActor::RegisterSD)
        .def_readwrite("actions", &GamVActor::actions)
        .def_readonly("batch_step_count", &GamVActor::batch_step_count)
        .def_readwrite("batch_size", &GamVActor::batch_size)
        .def("ActorInitialize", &GamVActor::ActorInitialize)
        .def("StartSimulationAction", &GamVActor::StartSimulationAction)
        .def("EndSimulationAction", &GamVActor::EndSimulationAction)
        .def("ProcessHitsPerBatch", &GamVActor::ProcessHitsPerBatch)
        .def("SteppingBatchAction", &GamVActor::SteppingBatchAction)
        .def("BeginOfRunAction", &GamVActor::BeginOfRunAction)
        .def("EndOfRunAction", &GamVActor::EndOfRunAction)
        .def("BeginOfEventAction", &GamVActor::BeginOfEventAction)
        .def("EndOfEventAction", &GamVActor::EndOfEventAction)
        .def("PreUserTrackingAction", &GamVActor::PreUserTrackingAction)
        .def("PostUserTrackingAction", &GamVActor::PostUserTrackingAction);
}

