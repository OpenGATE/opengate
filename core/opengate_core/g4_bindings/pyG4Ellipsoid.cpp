/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Ellipsoid.hh"

void init_G4Ellipsoid(py::module &m) {
  py::class_<G4Ellipsoid, G4VSolid, std::unique_ptr<G4Ellipsoid, py::nodelete>>(m, "G4Ellipsoid")
    // add function
    .def(py::init<const G4String &, G4double, G4double, G4double, G4double, G4double>(),
         py::arg("pName"),
         py::arg("pXSemiAxis"),
         py::arg("pYSemiAxis"),
         py::arg("pZSemiAxis"),
         py::arg("pZCut1"),
         py::arg("pZCut2"));

   
}

