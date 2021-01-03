/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4PrimaryVertex.hh"

void init_G4PrimaryVertex(py::module &m) {
    py::class_<G4PrimaryVertex>(m, "G4PrimaryVertex")

            .def(py::init())
            .def("GetPosition", &G4PrimaryVertex::GetPosition)
            .def("GetNumberOfParticle", &G4PrimaryVertex::GetNumberOfParticle);
}
