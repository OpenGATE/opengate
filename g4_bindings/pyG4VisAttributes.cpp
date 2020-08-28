/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4VisAttributes.hh"

void init_G4VisAttributes(py::module &m) {
    py::class_<G4VisAttributes>(m, "G4VisAttributes")

        .def(py::init<>())
        .def("SetColor",
             [](G4VisAttributes &va, G4double red,
                G4double green, G4double blue, G4double alpha) {
                 va.SetColor(red, green, blue, alpha);
             }
        );
}

