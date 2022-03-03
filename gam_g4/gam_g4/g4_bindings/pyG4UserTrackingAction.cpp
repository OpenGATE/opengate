/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4UserTrackingAction.hh"
#include "G4Track.hh"

class PyG4UserTrackingAction : public G4UserTrackingAction {
public:
    /* Inherit the constructors */
    using G4UserTrackingAction::G4UserTrackingAction;

    void PreUserTrackingAction(const G4Track *aTrack) override {
        PYBIND11_OVERLOAD(void,
                          G4UserTrackingAction,
                          PreUserTrackingAction,
                          aTrack
        );
    }

    void PostUserTrackingAction(const G4Track *aTrack) override {
        PYBIND11_OVERLOAD(void,
                          G4UserTrackingAction,
                          PostUserTrackingAction,
                          aTrack
        );
    }
};

void init_G4UserTrackingAction(py::module &m) {

    py::class_<G4UserTrackingAction, PyG4UserTrackingAction>(m, "G4UserTrackingAction")
        .def(py::init())
        .def("PreUserTrackingAction", &G4UserTrackingAction::PreUserTrackingAction)
        .def("PostUserTrackingAction", &G4UserTrackingAction::PostUserTrackingAction);
}

