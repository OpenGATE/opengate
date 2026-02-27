/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateBooleanFilter.h"

void init_GateBooleanFilter(py::module &m) {
  py::class_<GateBooleanFilter, GateVFilter>(m, "GateBooleanFilter")
      .def(py::init())
      .def("InitializeUserInfo", &GateBooleanFilter::InitializeUserInfo);
}