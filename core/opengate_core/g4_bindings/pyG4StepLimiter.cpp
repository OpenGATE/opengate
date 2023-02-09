/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4StepLimiter.hh"
#include "G4VProcess.hh"

void init_G4StepLimiter(py::module &m) {

  py::class_<G4StepLimiter, G4VProcess,
             std::unique_ptr<G4StepLimiter, py::nodelete>>(m, "G4StepLimiter")
      .def(py::init<const G4String &>());
}
