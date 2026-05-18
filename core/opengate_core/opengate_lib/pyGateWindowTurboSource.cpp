/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateWindowTurboSource.h"

void init_GateWindowTurboSource(py::module &m) {

  py::class_<GateWindowTurboSource, GateGenericSource>(m,
                                                       "GateWindowTurboSource")
      .def(py::init())
      .def("InitializeUserInfo", &GateWindowTurboSource::InitializeUserInfo)
      .def("ViusalizeWindow", &GateWindowTurboSource::ViusalizeWindow);
}
