/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/operators.h>

namespace py = pybind11;

#include "G4Transform3D.hh"

void init_G4Transform3D(py::module &m) {
    py::class_<G4Transform3D>(m, "G4Transform3D")

        // constructors 4x3 transformation matrix
        .def(py::init<>())
        .def(py::init<const CLHEP::HepRotation &, const CLHEP::Hep3Vector &>());

}

