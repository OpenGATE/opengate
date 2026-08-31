/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVDigitizerWithOutputActor.h"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

void init_GateVDigitizerWithOutputActor(py::module &m) {

  py::class_<GateVDigitizerWithOutputActor,
             std::unique_ptr<GateVDigitizerWithOutputActor, py::nodelete>,
             GateVActor>(m, "GateVDigitizerWithOutputActor")
      .def(py::init<py::dict &, bool>());
}
