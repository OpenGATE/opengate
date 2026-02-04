/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4ClassicalRK4.hh"

void init_G4ClassicalRK4(py::module &m) {
  py::class_<G4ClassicalRK4, std::unique_ptr<G4ClassicalRK4, py::nodelete>>(
      m, "G4ClassicalRK4")

    .def(py::init<G4EquationOfMotion*, G4int>());

}
