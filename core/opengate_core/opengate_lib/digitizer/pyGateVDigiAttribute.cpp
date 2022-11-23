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

#include "GateVDigiAttribute.h"

void init_GateVDigiAttribute(py::module &m) {
  py::class_<GateVDigiAttribute,
             std::unique_ptr<GateVDigiAttribute, py::nodelete>>(
      m, "GateVDigiAttribute")
      .def("GetDigiAttributeName", &GateVDigiAttribute::GetDigiAttributeName)
      .def("GetDigiAttributeType", &GateVDigiAttribute::GetDigiAttributeType)
      .def("FillDValue", &GateVDigiAttribute::FillDValue)
      .def("FillSValue", &GateVDigiAttribute::FillSValue)
      .def("FillIValue", &GateVDigiAttribute::FillIValue)
      .def("Fill3Value", &GateVDigiAttribute::Fill3Value);
}
