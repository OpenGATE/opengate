/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateScatterFilter.h"
#include "GateVFilter.h"

void init_GateScatterFilter(py::module &m) {
  py::class_<GateScatterFilter, GateVFilter>(m, "GateScatterFilter")
      .def(py::init())
      .def("Initialize", &GateScatterFilter::Initialize);
}
