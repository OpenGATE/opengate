/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateDigitizerEnergyWindowsActor.h"

void init_GateDigitizerEnergyWindowsActor(py::module &m) {

  py::class_<GateDigitizerEnergyWindowsActor,
             std::unique_ptr<GateDigitizerEnergyWindowsActor, py::nodelete>,
             GateVActor>(m, "GateDigitizerEnergyWindowsActor")
      .def(py::init<py::dict &>());
}
