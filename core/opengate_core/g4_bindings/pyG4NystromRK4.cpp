/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4MagIntegratorStepper.hh"
#include "G4Mag_EqRhs.hh"
#include "G4NystromRK4.hh"

void init_G4NystromRK4(py::module &m) {
  // G4NystromRK4 inherits from G4MagIntegratorStepper
  py::class_<G4NystromRK4, G4MagIntegratorStepper,
             std::unique_ptr<G4NystromRK4, py::nodelete>>(m, "G4NystromRK4")

      .def(py::init<G4Mag_EqRhs *, G4double>(), py::arg("equation"),
           py::arg("distanceConstField") = 0.0)

      ;
}
