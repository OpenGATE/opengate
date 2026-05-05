/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4ElectricField.hh"
#include "G4UniformElectricField.hh"

void init_G4UniformElectricField(py::module &m) {

  py::class_<G4UniformElectricField, G4ElectricField,
             std::unique_ptr<G4UniformElectricField, py::nodelete>>(
      m, "G4UniformElectricField")

      .def(py::init<const G4ThreeVector &>())
      .def(py::init<G4double, G4double, G4double>())

      ;
}
