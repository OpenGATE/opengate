/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateChemistryController.h"

void init_GateChemistryController(py::module &m) {
  py::class_<GateChemistryController,
             std::unique_ptr<GateChemistryController, py::nodelete>,
             GateVChemistryActor>(m, "GateChemistryController")
      .def(py::init<py::dict &>())
      .def("StartChemistryTracking",
           &GateChemistryController::StartChemistryTracking);
}
