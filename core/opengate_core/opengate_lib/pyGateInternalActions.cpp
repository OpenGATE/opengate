/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateInternalActions.h"

void init_GateInternalActions(py::module &m) {
  py::class_<GateInternalActions,
             std::unique_ptr<GateInternalActions, py::nodelete>, GateVActor>(
      m, "GateInternalActions")
      .def(py::init<py::dict &>());
}
