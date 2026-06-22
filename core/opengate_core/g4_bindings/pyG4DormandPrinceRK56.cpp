/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include <G4DormandPrinceRK56.hh>
#include <G4EquationOfMotion.hh>
#include <G4MagIntegratorStepper.hh>

void init_G4DormandPrinceRK56(py::module &m) {
  // G4DormandPrinceRK56 inherits from G4MagIntegratorStepper
  py::class_<G4DormandPrinceRK56, G4MagIntegratorStepper,
             std::unique_ptr<G4DormandPrinceRK56, py::nodelete>>(
      m, "G4DormandPrinceRK56")

      .def(py::init<G4EquationOfMotion *, G4int>())

      ;
}
