/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4UserRunAction.hh"
#include "G4Run.hh"

class PyG4UserRunAction : public G4UserRunAction {
public:
    /* Inherit the constructors */
    using G4UserRunAction::G4UserRunAction;

    void BeginOfRunAction(const G4Run *aRun) override {
        PYBIND11_OVERLOAD(void,
                          G4UserRunAction,
                          BeginOfRunAction,
                          aRun
        );
    }

    void EndOfRunAction(const G4Run *aRun) override {
        PYBIND11_OVERLOAD(void,
                          G4UserRunAction,
                          EndOfRunAction,
                          aRun
        );
    }
};

void init_G4UserRunAction(py::module &m) {

    py::class_<G4UserRunAction, PyG4UserRunAction>(m, "G4UserRunAction")
            .def(py::init())
            .def("BeginOfRunAction", &G4UserRunAction::BeginOfRunAction)
            .def("EndOfRunAction", &G4UserRunAction::EndOfRunAction);
}

