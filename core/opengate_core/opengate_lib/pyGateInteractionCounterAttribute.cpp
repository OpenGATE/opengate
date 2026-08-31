/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateInteractionCounterAttribute.h"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

void init_GateInteractionCounterAttribute(py::module &m) {
  py::class_<GateInteractionCounterAttribute, GateVAuxiliaryAttribute>(
      m, "GateInteractionCounterAttribute")
      .def(py::init<py::dict &>());
}
