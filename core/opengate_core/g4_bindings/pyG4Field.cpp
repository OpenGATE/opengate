/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Field.hh"

void init_G4Field(py::module &m) {
  // G4Field is an abstract class with pure virtual functions:
  // - GetFieldValue()
  // - DoesFieldChangeEnergy()
  // Therefore, it cannot be instantiated directly from Python.
  py::class_<G4Field, std::unique_ptr<G4Field, py::nodelete>>(
      m, "G4Field")

    // No constructors - abstract class cannot be instantiated

    .def("DoesFieldChangeEnergy", &G4Field::DoesFieldChangeEnergy)

    .def("IsGravityActive", &G4Field::IsGravityActive)
    .def("SetGravityActive", &G4Field::SetGravityActive);

}
