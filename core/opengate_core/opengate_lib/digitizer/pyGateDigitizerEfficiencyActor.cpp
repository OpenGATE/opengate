/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateDigitizerEfficiencyActor.h"

void init_GateDigitizerEfficiencyActor(py::module &m) {

  py::class_<GateDigitizerEfficiencyActor,
             std::unique_ptr<GateDigitizerEfficiencyActor, py::nodelete>,
             GateVActor>(m, "GateDigitizerEfficiencyActor")
      .def(py::init<py::dict &>());
}
