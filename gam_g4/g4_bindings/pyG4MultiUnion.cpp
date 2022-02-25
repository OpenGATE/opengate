/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4MultiUnion.hh"
#include "G4VSolid.hh"

void init_G4MultiUnion(py::module &m) {
    py::class_<G4MultiUnion, G4VSolid>(m, "G4MultiUnion")

        .def(py::init<const G4String &>())
        .def("Voxelize", &G4MultiUnion::Voxelize)
        .def("AddNode", &G4MultiUnion::AddNode);
}
