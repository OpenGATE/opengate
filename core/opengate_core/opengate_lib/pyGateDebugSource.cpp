/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateDebugSource.h"

void init_GateDebugSource(py::module &m) {

  py::class_<GateDebugSource, GateVSource>(m, "GateDebugSource")
      .def(py::init());
}
