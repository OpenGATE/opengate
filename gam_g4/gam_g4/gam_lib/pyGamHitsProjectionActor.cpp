/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamHitsProjectionActor.h"

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html#virtual-and-inheritance

class PyGamHitsProjectionActor : public GamHitsProjectionActor {
public:
    // Inherit the constructors
    using GamHitsProjectionActor::GamHitsProjectionActor;

    void SteppingAction(G4Step *step,
                        G4TouchableHistory *touchable) override {
        PYBIND11_OVERLOAD(void, GamHitsProjectionActor, SteppingAction, step, touchable);
    }

    void BeginOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamHitsProjectionActor, BeginOfRunAction, Run);
    }

    void EndOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamHitsProjectionActor, EndOfRunAction, Run);
    }

    void BeginOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamHitsProjectionActor, BeginOfEventAction, event);
    }

    void EndOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamHitsProjectionActor, EndOfEventAction, event);
    }

    void PreUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamHitsProjectionActor, PreUserTrackingAction, track);
    }

    void PostUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamHitsProjectionActor, PostUserTrackingAction, track);
    }

};

void init_GamHitsProjectionActor(py::module &m) {

    py::class_<GamHitsProjectionActor,
        PyGamHitsProjectionActor,
        std::unique_ptr<GamHitsProjectionActor, py::nodelete>,
        GamVActor>(m, "GamHitsProjectionActor")
        .def(py::init<py::dict &>())
        .def_readwrite("fImage", &GamHitsProjectionActor::fImage)
        .def_readwrite("fPhysicalVolumeName", &GamHitsProjectionActor::fPhysicalVolumeName);
}

