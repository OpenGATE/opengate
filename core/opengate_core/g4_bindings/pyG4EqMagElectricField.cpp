/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4ElectroMagneticField.hh"
#include "G4EqMagElectricField.hh"
#include "G4EquationOfMotion.hh"

void init_G4EqMagElectricField(py::module &m) {

  py::class_<G4EqMagElectricField, G4EquationOfMotion,
             std::unique_ptr<G4EqMagElectricField, py::nodelete>>(
      m, "G4EqMagElectricField")

      .def(py::init<G4ElectroMagneticField *>())

      .def("SetChargeMomentumMass", &G4EqMagElectricField::SetChargeMomentumMass)

      ;
}
