/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateHitsEnergyWindowsActor.h"

void init_GateHitsEnergyWindowsActor(py::module &m) {

  py::class_<GateHitsEnergyWindowsActor,
             std::unique_ptr<GateHitsEnergyWindowsActor, py::nodelete>,
             GateVActor>(m, "GateHitsEnergyWindowsActor")
      .def(py::init<py::dict &>());
}
