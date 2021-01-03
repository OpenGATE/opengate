/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Trap.hh"

void init_G4Trap(py::module &m) {
    py::class_<G4Trap, G4VSolid>(m, "G4Trap")

            .def(py::init<const G4String &, G4double, G4double,
                    G4double, G4double, G4double, G4double,
                    G4double, G4double, G4double, G4double, G4double>());
}
