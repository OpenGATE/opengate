/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateARFActor.h"

void init_GateARFActor(py::module &m) {
  py::class_<GateARFActor, std::unique_ptr<GateARFActor, py::nodelete>,
             GateVActor>(m, "GateARFActor")
      .def(py::init<py::dict &>())
      .def("SetARFFunction", &GateARFActor::SetARFFunction)
      .def("GetCurrentNumberOfHits", &GateARFActor::GetCurrentNumberOfHits)
      .def("GetCurrentRunId", &GateARFActor::GetCurrentRunId)
      .def("GetEnergy", &GateARFActor::GetEnergy)
      .def("GetPositionX", &GateARFActor::GetPositionX)
      .def("GetPositionY", &GateARFActor::GetPositionY)
      .def("GetDirectionX", &GateARFActor::GetDirectionX)
      .def("GetDirectionY", &GateARFActor::GetDirectionY)
      .def("GetDirectionZ", &GateARFActor::GetDirectionZ);
}
