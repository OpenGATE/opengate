/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateThresholdAttributeFilter.h"

void init_GateThresholdAttributeFilter(py::module &m) {
  py::class_<GateThresholdAttributeFilter, GateVFilter>(
      m, "GateThresholdAttributeFilter")
      .def(py::init())
      .def("Initialize", &GateThresholdAttributeFilter::Initialize);
}
