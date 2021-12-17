/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamHitsCollectionActor.h"

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html#virtual-and-inheritance

class PyGamHitsCollectionActor : public GamHitsCollectionActor {
public:
    // Inherit the constructors
    using GamHitsCollectionActor::GamHitsCollectionActor;

    void SteppingAction(G4Step *step,
                        G4TouchableHistory *touchable) override {
        PYBIND11_OVERLOAD(void, GamHitsCollectionActor, SteppingAction, step, touchable);
    }

    void BeginOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamHitsCollectionActor, BeginOfRunAction, Run);
    }

    void EndOfRunAction(const G4Run *Run) override {
        PYBIND11_OVERLOAD(void, GamHitsCollectionActor, EndOfRunAction, Run);
    }

    void BeginOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamHitsCollectionActor, BeginOfEventAction, event);
    }

    void EndOfEventAction(const G4Event *event) override {
        PYBIND11_OVERLOAD(void, GamHitsCollectionActor, EndOfEventAction, event);
    }

    void PreUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamHitsCollectionActor, PreUserTrackingAction, track);
    }

    void PostUserTrackingAction(const G4Track *track) override {
        PYBIND11_OVERLOAD(void, GamHitsCollectionActor, PostUserTrackingAction, track);
    }

};

void init_GamHitsCollectionActor(py::module &m) {

    py::class_<GamHitsCollectionActor, PyGamHitsCollectionActor,
        std::unique_ptr<GamHitsCollectionActor //,py::nodelete
        >, GamVActor>(m, "GamHitsCollectionActor")
        .def(py::init<py::dict &>())
        //.def("GetHits", &GamHitsCollectionActor::GetHits)
        //.def_readwrite("fStepFillNames", &GamHitsCollectionActor::fStepFillNames)
        ;
}

