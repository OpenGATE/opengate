/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4MagneticField.hh"
#include "G4QuadrupoleMagField.hh"

void init_G4QuadrupoleMagField(py::module &m) {

  py::class_<G4QuadrupoleMagField, G4MagneticField, std::unique_ptr<G4QuadrupoleMagField, py::nodelete>>(
      m, "G4QuadrupoleMagField")

  .def(py::init<G4double>())

  ;

}
