/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4MagIntegratorStepper.hh"
#include "G4EquationOfMotion.hh"

void init_G4MagIntegratorStepper(py::module &m) {
  // G4MagIntegratorStepper is an abstract class with pure virtual functions:
  // - Stepper()
  // - DistChord()
  // - IntegratorOrder()
  // Therefore, it cannot be instantiated directly from Python.
  py::class_<G4MagIntegratorStepper, std::unique_ptr<G4MagIntegratorStepper, py::nodelete>>(
      m, "G4MagIntegratorStepper")

    // No constructors - abstract class cannot be instantiated

    .def("GetNumberOfVariables", &G4MagIntegratorStepper::GetNumberOfVariables)
    .def("GetNumberOfStateVariables", &G4MagIntegratorStepper::GetNumberOfStateVariables)
    .def("IntegratorOrder", &G4MagIntegratorStepper::IntegratorOrder)
    ;
}
