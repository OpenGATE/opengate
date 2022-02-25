/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamPhaseSpaceActor.h"

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html#virtual-and-inheritance

class PyGamPhaseSpaceActor : public GamPhaseSpaceActor {
public:
    // Inherit the constructors
    using GamPhaseSpaceActor::GamPhaseSpaceActor;

    void SteppingAction(G4Step *step,
                        G4TouchableHistory *touchable) override {
        PYBIND11_OVERLOAD(void, GamPhaseSpaceActor, SteppingAction, step, touchable);
    }

    void BeginOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamPhaseSpaceActor, BeginOfRunAction, Run);
    }

    void EndOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamPhaseSpaceActor, EndOfRunAction, Run);
    }

    void BeginOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamPhaseSpaceActor, BeginOfEventAction, event);
    }

    void EndOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamPhaseSpaceActor, EndOfEventAction, event);
    }

    void PreUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamPhaseSpaceActor, PreUserTrackingAction, track);
    }

    void PostUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamPhaseSpaceActor, PostUserTrackingAction, track);
    }

};

void init_GamPhaseSpaceActor(py::module &m) {

    py::class_<GamPhaseSpaceActor, PyGamPhaseSpaceActor,
        std::unique_ptr<GamPhaseSpaceActor //,py::nodelete
        >, GamVActor>(m, "GamPhaseSpaceActor")
        .def(py::init<py::dict &>());
}

