/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4EquationOfMotion.hh"

void init_G4EquationOfMotion(py::module &m) {
  // G4EquationOfMotion is an abstract class with pure virtual functions:
  // - EvaluateRhsGivenB()
  // - SetChargeMomentumMass()
  // Therefore, it cannot be instantiated directly from Python.
  py::class_<G4EquationOfMotion, std::unique_ptr<G4EquationOfMotion, py::nodelete>>(
      m, "G4EquationOfMotion")

    // No constructors - abstract class cannot be instantiated

    .def("GetFieldObj", py::overload_cast<>(&G4EquationOfMotion::GetFieldObj, py::const_),
        py::return_value_policy::reference_internal)
    ;
}
