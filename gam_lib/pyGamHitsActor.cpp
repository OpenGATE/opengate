/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamHitsActor.h"

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html#virtual-and-inheritance

class PyGamHitsActor : public GamHitsActor {
public:
    // Inherit the constructors
    using GamHitsActor::GamHitsActor;

    void SteppingAction(G4Step *step,
                        G4TouchableHistory *touchable) override {
        PYBIND11_OVERLOAD(void, GamHitsActor, SteppingAction, step, touchable);
    }

    void BeginOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamHitsActor, BeginOfRunAction, Run);
    }

    void EndOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamHitsActor, EndOfRunAction, Run);
    }

    void BeginOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamHitsActor, BeginOfEventAction, event);
    }

    void EndOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamHitsActor, EndOfEventAction, event);
    }

    void PreUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamHitsActor, PreUserTrackingAction, track);
    }

    void PostUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamHitsActor, PostUserTrackingAction, track);
    }

};

void init_GamHitsActor(py::module &m) {

    py::class_<GamHitsActor, PyGamHitsActor,
        std::unique_ptr<GamHitsActor, py::nodelete>, GamVActor>(m, "GamHitsActor")
        .def(py::init<py::dict &>())
        .def_readwrite("fActions", &GamHitsActor::fActions)
        .def_readwrite("fStepFillNames", &GamHitsActor::fStepFillNames);
}

