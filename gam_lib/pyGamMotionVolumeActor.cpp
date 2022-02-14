/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamMotionVolumeActor.h"

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html#virtual-and-inheritance

class PyGamMotionVolumeActor : public GamMotionVolumeActor {
public:
    // Inherit the constructors
    using GamMotionVolumeActor::GamMotionVolumeActor;

    void SteppingAction(G4Step *step,
                        G4TouchableHistory *touchable) override {
        PYBIND11_OVERLOAD(void, GamMotionVolumeActor, SteppingAction, step, touchable);
    }

    void BeginOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamMotionVolumeActor, BeginOfRunAction, Run);
    }

    void EndOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamMotionVolumeActor, EndOfRunAction, Run);
    }

    void BeginOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamMotionVolumeActor, BeginOfEventAction, event);
    }

    void EndOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamMotionVolumeActor, EndOfEventAction, event);
    }

    void PreUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamMotionVolumeActor, PreUserTrackingAction, track);
    }

    void PostUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamMotionVolumeActor, PostUserTrackingAction, track);
    }

};

void init_GamMotionVolumeActor(py::module &m) {

    py::class_<GamMotionVolumeActor,
        PyGamMotionVolumeActor,
        std::unique_ptr<GamMotionVolumeActor, py::nodelete>,
        GamVActor>(m, "GamMotionVolumeActor")
        .def(py::init<py::dict &>());
}

