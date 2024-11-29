/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GatePrimaryScatterFilter.h"
#include "GateVFilter.h"

void init_GatePrimaryScatterFilter(py::module &m) {
  py::class_<GateUnscatteredPrimaryFilter, GateVFilter>(
      m, "GateUnscatteredPrimaryFilter")
      .def(py::init())
      .def("InitializeUserInfo",
           &GateUnscatteredPrimaryFilter::InitializeUserInfo);
}
