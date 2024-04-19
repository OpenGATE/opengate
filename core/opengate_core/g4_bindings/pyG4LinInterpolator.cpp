/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4LinInterpolator.hh"

void init_G4LinInterpolator(py::module &m) {
  py::class_<G4LinInterpolator, G4IInterpolator>(m, "G4LinInterpolator")
      .def(py::init<>());
}
