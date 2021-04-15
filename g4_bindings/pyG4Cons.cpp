/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Cons.hh"

void init_G4Cons(py::module &m) {
    py::class_<G4Cons, G4VSolid>(m, "G4Cons")

        .def(py::init<const G4String &, G4double, G4double,
            G4double, G4double, G4double, G4double, G4double>());
}
