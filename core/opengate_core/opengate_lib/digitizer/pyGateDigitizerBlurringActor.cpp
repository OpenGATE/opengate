/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateDigitizerBlurringActor.h"

void init_GateDigitizerBlurringActor(py::module &m) {

  py::class_<GateDigitizerBlurringActor,
             std::unique_ptr<GateDigitizerBlurringActor, py::nodelete>,
             GateVDigitizerWithOutputActor>(m, "GateDigitizerBlurringActor")
      .def(py::init<py::dict &>());
}
