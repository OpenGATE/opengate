/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4ClassicalRK4.hh"
#include "G4EquationOfMotion.hh"
#include "G4MagErrorStepper.hh"

void init_G4ClassicalRK4(py::module &m) {
  // G4ClassicalRK4 inherits from G4MagErrorStepper
  py::class_<G4ClassicalRK4, G4MagErrorStepper,
             std::unique_ptr<G4ClassicalRK4, py::nodelete>>(m, "G4ClassicalRK4")

      .def(py::init<G4EquationOfMotion *, G4int>())

      ;
}
