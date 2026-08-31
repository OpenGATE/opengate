/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GatePencilBeamSource.h"
#include <pybind11/pybind11.h>

void init_GatePencilBeamSource(py::module &m) {

  py::class_<GatePencilBeamSource, GateGenericSource>(m, "GatePencilBeamSource")
      .def(py::init())
      .def("InitializeUserInfo", &GatePencilBeamSource::InitializeUserInfo);
}
