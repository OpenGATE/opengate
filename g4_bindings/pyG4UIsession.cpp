/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4UIsession.hh"

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html
// Needed helper class because of the pure virtual method
class PyG4UIsession : public G4UIsession {
public:
    // Inherit the constructors
    using G4UIsession::G4UIsession;

    // Trampoline (need one for each virtual function)
    G4int ReceiveG4cout(const G4String &coutString) override {
        PYBIND11_OVERLOAD(G4int,
                          G4UIsession,
                          ReceiveG4cout,
                          coutString);

    }

    // Trampoline (need one for each virtual function)
    G4int ReceiveG4cerr(const G4String &cerrString) override {
        PYBIND11_OVERLOAD(G4int,
                          G4UIsession,
                          ReceiveG4cerr,
                          cerrString);
    }
};


void init_G4UIsession(py::module &m) {

    py::class_<G4UIsession, PyG4UIsession>(m, "G4UIsession")
        .def(py::init())
        .def(py::init<G4int>())
        .def("ReceiveG4cout", &G4UIsession::ReceiveG4cout)
        .def("ReceiveG4cerr", &G4UIsession::ReceiveG4cerr);

}
