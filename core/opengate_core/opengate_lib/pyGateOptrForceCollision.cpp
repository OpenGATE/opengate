/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;
#include "G4VBiasingOperator.hh"
#include "GateOptrForceCollision.h"

void init_GateOptrForceCollision(py::module &m) {

  py::class_<GateOptrForceCollision, G4VBiasingOperator, GateVActor,
             std::unique_ptr<GateOptrForceCollision, py::nodelete>>(
      m, "GateOptrForceCollision")
      .def(py::init<py::dict &>());
}
