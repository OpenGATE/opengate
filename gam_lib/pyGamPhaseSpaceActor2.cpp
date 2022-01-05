/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamPhaseSpaceActor2.h"

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html#virtual-and-inheritance

class PyGamPhaseSpaceActor2 : public GamPhaseSpaceActor2 {
public:
    // Inherit the constructors
    using GamPhaseSpaceActor2::GamPhaseSpaceActor2;

    void SteppingAction(G4Step *step,
                        G4TouchableHistory *touchable) override {
        PYBIND11_OVERLOAD(void, GamPhaseSpaceActor2, SteppingAction, step, touchable);
    }

    void BeginOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamPhaseSpaceActor2, BeginOfRunAction, Run);
    }

    void EndOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamPhaseSpaceActor2, EndOfRunAction, Run);
    }

    void BeginOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamPhaseSpaceActor2, BeginOfEventAction, event);
    }

    void EndOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamPhaseSpaceActor2, EndOfEventAction, event);
    }

    void PreUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamPhaseSpaceActor2, PreUserTrackingAction, track);
    }

    void PostUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamPhaseSpaceActor2, PostUserTrackingAction, track);
    }

};

void init_GamPhaseSpaceActor2(py::module &m) {

    py::class_<GamPhaseSpaceActor2, PyGamPhaseSpaceActor2,
        std::unique_ptr<GamPhaseSpaceActor2 //,py::nodelete
        >, GamVActor>(m, "GamPhaseSpaceActor2")
        .def(py::init<py::dict &>());
}

