/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVAuxiliaryAttribute.h"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

void init_GateVAuxiliaryAttribute(py::module &m) {
  py::class_<GateVAuxiliaryAttribute>(m, "GateVAuxiliaryAttribute")
      .def(py::init<py::dict &>())
      .def("InitializeUserInfo", &GateVAuxiliaryAttribute::InitializeUserInfo)
      .def("InitializeCpp", &GateVAuxiliaryAttribute::InitializeCpp)
      .def("AddActions", &GateVAuxiliaryAttribute::AddActions)
      .def("HasAction", &GateVAuxiliaryAttribute::HasAction)
      .def("GetName", &GateVAuxiliaryAttribute::GetName)
      .def("GetTrackDataSlotID", &GateVAuxiliaryAttribute::GetTrackDataSlotID)
      .def("GetDigiAttributeType",
           &GateVAuxiliaryAttribute::GetDigiAttributeType)
      .def_static("ClearRegistry", &GateVAuxiliaryAttribute::ClearRegistry);
}
