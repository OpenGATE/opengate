/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4IntersectionSolid.hh"
#include "G4VSolid.hh"

void init_G4IntersectionSolid(py::module &m) {
    py::class_<G4IntersectionSolid, G4VSolid>(m, "G4IntersectionSolid")

        .def(py::init<const G4String &, G4VSolid *, G4VSolid *, G4RotationMatrix *, const G4ThreeVector &>());
}
