/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamHitsEnergyWindowsActor.h"

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html#virtual-and-inheritance

class PyGamHitsEnergyWindowsActor : public GamHitsEnergyWindowsActor {
public:
    // Inherit the constructors
    using GamHitsEnergyWindowsActor::GamHitsEnergyWindowsActor;

    void SteppingAction(G4Step *step,
                        G4TouchableHistory *touchable) override {
        PYBIND11_OVERLOAD(void, GamHitsEnergyWindowsActor, SteppingAction, step, touchable);
    }

    void BeginOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamHitsEnergyWindowsActor, BeginOfRunAction, Run);
    }

    void EndOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamHitsEnergyWindowsActor, EndOfRunAction, Run);
    }

    void BeginOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamHitsEnergyWindowsActor, BeginOfEventAction, event);
    }

    void EndOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamHitsEnergyWindowsActor, EndOfEventAction, event);
    }

    void PreUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamHitsEnergyWindowsActor, PreUserTrackingAction, track);
    }

    void PostUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamHitsEnergyWindowsActor, PostUserTrackingAction, track);
    }

};

void init_GamHitsEnergyWindowsActor(py::module &m) {

    py::class_<GamHitsEnergyWindowsActor,
        PyGamHitsEnergyWindowsActor,
        std::unique_ptr<GamHitsEnergyWindowsActor, py::nodelete>,
        GamVActor>(m, "GamHitsEnergyWindowsActor")
        .def(py::init<py::dict &>());
}

