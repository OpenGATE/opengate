/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateChemistryLongTimeActor.h"

void init_GateChemistryLongTimeActor(py::module &m) {
  py::class_<GateChemistryLongTimeActor,
             std::unique_ptr<GateChemistryLongTimeActor, py::nodelete>,
             GateVActor>(m, "GateChemistryLongTimeActor")
      .def(py::init<py::dict &>())
      .def("get_times", &GateChemistryLongTimeActor::getTimes)
      .def("get_data", &GateChemistryLongTimeActor::getData);
}
