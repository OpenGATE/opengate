/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Tubs.hh"

void init_G4Tubs(py::module &m) {
    py::class_<G4Tubs, G4VSolid>(m, "G4Tubs")

        .def(py::init<const G4String &, G4double, G4double,
            G4double, G4double, G4double>());
}
