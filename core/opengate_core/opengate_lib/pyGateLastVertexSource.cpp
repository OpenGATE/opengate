/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateLastVertexSource.h"
#include <pybind11/pybind11.h>

void init_GateLastVertexSource(py::module &m) {

  py::class_<GateLastVertexSource, GateVSource>(m, "GateLastVertexSource")
      .def(py::init())
      .def("InitializeUserInfo", &GateLastVertexSource::InitializeUserInfo)
      .def("GetTotalReplayedEvents",
           &GateLastVertexSource::GetTotalReplayedEvents);
}
