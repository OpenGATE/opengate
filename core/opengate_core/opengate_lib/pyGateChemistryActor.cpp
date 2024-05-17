/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateChemistryActor.h"

void init_GateChemistryActor(py::module &m) {
  py::class_<GateChemistryActor,
             std::unique_ptr<GateChemistryActor, py::nodelete>, GateVActor>(
      m, "GateChemistryActor")
      .def(py::init<py::dict &>())
      .def("get_times", &GateChemistryActor::getTimes)
      .def("get_data", &GateChemistryActor::getData);
}
