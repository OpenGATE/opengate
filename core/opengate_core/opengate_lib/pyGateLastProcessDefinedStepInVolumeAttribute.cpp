/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateLastProcessDefinedStepInVolumeAttribute.h"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

void init_GateLastProcessDefinedStepInVolumeAttribute(py::module &m) {
  py::class_<GateLastProcessDefinedStepInVolumeAttribute,
             GateVAuxiliaryAttribute>(
      m, "GateLastProcessDefinedStepInVolumeAttribute")
      .def(py::init<py::dict &>());
}
