/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4MagErrorStepper.hh"
#include "G4MagIntegratorStepper.hh"

void init_G4MagErrorStepper(py::module &m) {
  // G4MagErrorStepper is an abstract class with pure virtual function:
  // - DumbStepper()
  // Therefore, it cannot be instantiated directly from Python.
  // It inherits from G4MagIntegratorStepper.
  py::class_<G4MagErrorStepper, G4MagIntegratorStepper, std::unique_ptr<G4MagErrorStepper, py::nodelete>>(
      m, "G4MagErrorStepper")

    // No constructors - abstract class cannot be instantiated
    ;
}
