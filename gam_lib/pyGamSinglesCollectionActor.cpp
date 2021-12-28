/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamSinglesCollectionActor.h"

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html#virtual-and-inheritance

class PyGamSinglesCollectionActor : public GamSinglesCollectionActor {
public:
    // Inherit the constructors
    using GamSinglesCollectionActor::GamSinglesCollectionActor;

    void SteppingAction(G4Step *step,
                        G4TouchableHistory *touchable) override {
        PYBIND11_OVERLOAD(void, GamSinglesCollectionActor, SteppingAction, step, touchable);
    }

    void BeginOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamSinglesCollectionActor, BeginOfRunAction, Run);
    }

    void EndOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamSinglesCollectionActor, EndOfRunAction, Run);
    }

    void BeginOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamSinglesCollectionActor, BeginOfEventAction, event);
    }

    void EndOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamSinglesCollectionActor, EndOfEventAction, event);
    }

    void PreUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamSinglesCollectionActor, PreUserTrackingAction, track);
    }

    void PostUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamSinglesCollectionActor, PostUserTrackingAction, track);
    }

};

void init_GamSinglesCollectionActor(py::module &m) {

    py::class_<GamSinglesCollectionActor, PyGamSinglesCollectionActor,
        std::unique_ptr<GamSinglesCollectionActor //,py::nodelete
        >, GamVActor>(m, "GamSinglesCollectionActor")
        .def(py::init<py::dict &>());
}

