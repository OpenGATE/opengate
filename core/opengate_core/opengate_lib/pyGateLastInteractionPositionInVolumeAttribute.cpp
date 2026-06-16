/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateLastInteractionPositionInVolumeAttribute.h"

void init_GateLastInteractionPositionInVolumeAttribute(py::module &m) {
  py::class_<GateLastInteractionPositionInVolumeAttribute,
             GateVAuxiliaryAttribute>(
      m, "GateLastInteractionPositionInVolumeAttribute")
      .def(py::init<py::dict &>());
}
