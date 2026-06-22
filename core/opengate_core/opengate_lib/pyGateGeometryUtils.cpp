/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateGeometryUtils.h"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

void init_GateGeometryUtils(py::module &m) {
  m.def("FindAllTouchables", FindAllTouchables, py::arg("target_lv_name"),
        py::arg("world_name") = "");
}
