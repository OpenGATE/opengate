/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4MagneticField.hh"
#include "G4UniformMagField.hh"

void init_G4UniformMagField(py::module &m) {
  // G4UniformMagField inherits from G4MagneticField
  py::class_<G4UniformMagField, G4MagneticField, std::unique_ptr<G4UniformMagField, py::nodelete>>(
      m, "G4UniformMagField")

    .def(py::init<const G4ThreeVector &>())
    .def("SetFieldValue", py::overload_cast<const G4ThreeVector &>(&G4UniformMagField::SetFieldValue))
    .def("GetConstantFieldValue", &G4UniformMagField::GetConstantFieldValue)
    ;
}
