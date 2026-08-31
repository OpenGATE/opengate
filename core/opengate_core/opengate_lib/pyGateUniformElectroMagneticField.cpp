/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateUniformElectroMagneticField.h"
#include <G4ElectroMagneticField.hh>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

void init_GateUniformElectroMagneticField(py::module &m) {
  py::class_<GateUniformElectroMagneticField, G4ElectroMagneticField,
             std::unique_ptr<GateUniformElectroMagneticField, py::nodelete>>(
      m, "GateUniformElectroMagneticField")

      .def(py::init(
               [](G4ThreeVector e_field_vector, G4ThreeVector b_field_vector) {
                 return new GateUniformElectroMagneticField(e_field_vector,
                                                            b_field_vector);
               }),
           py::arg("e_field_vector"), py::arg("b_field_vector"));
}
