/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GatePBSource.h"

void init_GatePBSource(py::module &m) {

  py::class_<GatePBSource, GateGenericSource>(m, "GatePBSource")
      .def(py::init())
      .def("InitializeUserInfo", &GatePBSource::InitializeUserInfo);
}
