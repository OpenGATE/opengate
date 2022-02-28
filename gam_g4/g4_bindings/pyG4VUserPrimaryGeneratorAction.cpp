/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4Event.hh"

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html
// Needed helper class because of the pure virtual method
class PyG4VUserPrimaryGeneratorAction : public G4VUserPrimaryGeneratorAction {
public:
    // Inherit the constructors
    using G4VUserPrimaryGeneratorAction::G4VUserPrimaryGeneratorAction;

    // Trampoline (need one for each virtual function)
    void GeneratePrimaries(G4Event *anEvent) override {
        std::cout << "GeneratePrimaries pure virtual trampoline" << std::endl;
        PYBIND11_OVERLOAD_PURE(void,
                               G4VUserPrimaryGeneratorAction,
                               GeneratePrimaries,
                               anEvent
        );
    }

};

// Main wrapper
void init_G4VUserPrimaryGeneratorAction(py::module &m) {

    py::class_<G4VUserPrimaryGeneratorAction,
        std::unique_ptr<G4VUserPrimaryGeneratorAction, py::nodelete>,
        PyG4VUserPrimaryGeneratorAction>(m, "G4VUserPrimaryGeneratorAction")
        .def(py::init_alias())
        .def("GeneratePrimaries", &G4VUserPrimaryGeneratorAction::GeneratePrimaries);
}
