/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GatePositroniumSource.h"

void init_GatePositroniumSource(py::module &m) {

  py::class_<GatePositroniumSource, GateGenericSource>(m, "GatePositroniumSource")
      .def(py::init())
      .def("InitializeUserInfo", &GatePositroniumSource::InitializeUserInfo);
}
