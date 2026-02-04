/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Field.hh"
#include "G4MagneticField.hh"

void init_G4MagneticField(py::module &m) {
  // G4MagneticField is an abstract class with pure virtual function:
  // - GetFieldValue()
  // Therefore, it cannot be instantiated directly from Python.
  py::class_<G4MagneticField, G4Field, std::unique_ptr<G4MagneticField, py::nodelete>>(
      m, "G4MagneticField")

    // No constructors - abstract class cannot be instantiated

    .def("DoesFieldChangeEnergy", &G4MagneticField::DoesFieldChangeEnergy);

}
