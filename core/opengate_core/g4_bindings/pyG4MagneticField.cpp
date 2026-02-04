/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4MagneticField.hh"

void init_G4MagneticField(py::module &m) {
  py::class_<G4MagneticField, std::unique_ptr<G4MagneticField, py::nodelete>>(
      m, "G4MagneticField")

    .def(py::init<>())
    .def(py::init<G4MagneticField&>())

    .def("DoesFieldChangeEnergy", &DoesFieldChangeEnergy);
    .def("GetFieldValue", &GetFieldValue);

}
