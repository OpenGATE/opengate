/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4BogackiShampine23.hh"
#include "G4EquationOfMotion.hh"
#include "G4MagIntegratorStepper.hh"

void init_G4BogackiShampine23(py::module &m) {
  // G4BogackiShampine23 inherits from G4MagIntegratorStepper
  py::class_<G4BogackiShampine23, G4MagIntegratorStepper,
             std::unique_ptr<G4BogackiShampine23, py::nodelete>>(
      m, "G4BogackiShampine23")

      .def(py::init<G4EquationOfMotion *, G4int>())

      ;
}
