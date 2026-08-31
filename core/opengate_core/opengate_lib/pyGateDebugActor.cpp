/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateDebugActor.h"

void init_GateDebugActor(py::module &m) {
  py::class_<GateDebugActor, std::unique_ptr<GateDebugActor, py::nodelete>,
             GateVActor>(m, "GateDebugActor")
      .def(py::init<py::dict &>())
      .def("InitializeUserInfo", &GateDebugActor::InitializeUserInfo);
}
