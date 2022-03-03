/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4UserSteppingAction.hh"
#include "G4Step.hh"


class PyG4UserSteppingAction : public G4UserSteppingAction {
public:
    /* Inherit the constructors */
    using G4UserSteppingAction::G4UserSteppingAction;

    void UserSteppingAction(const G4Step *aStep) override {
        PYBIND11_OVERLOAD(void,
                          G4UserSteppingAction,
                          UserSteppingAction,
                          aStep
        );
    }
};


void init_G4UserSteppingAction(py::module &m) {

    py::class_<G4UserSteppingAction, PyG4UserSteppingAction>(m, "G4UserSteppingAction")
        .def(py::init())
        .def("UserSteppingAction", &G4UserSteppingAction::UserSteppingAction);
}

