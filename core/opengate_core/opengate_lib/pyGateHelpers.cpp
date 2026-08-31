/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include <pybind11/pybind11.h>

void init_GateHelpers(py::module &m) {
  m.def("DictGetG4RotationMatrix", DictGetG4RotationMatrix);
  m.def("createTestQtWindow", &createTestQtWindow);
}
