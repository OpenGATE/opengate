/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4ExactHelixStepper.hh"
#include "G4MagIntegratorStepper.hh"
#include "G4Mag_EqRhs.hh"

void init_G4ExactHelixStepper(py::module &m) {
  // G4ExactHelixStepper <- G4MagHelicalStepper <- G4MagIntegratorStepper.
  py::class_<G4ExactHelixStepper, G4MagIntegratorStepper,
             std::unique_ptr<G4ExactHelixStepper, py::nodelete>>(
      m, "G4ExactHelixStepper")

      .def(py::init<G4Mag_EqRhs *>())

      ;
}
