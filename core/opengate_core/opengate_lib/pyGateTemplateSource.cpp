/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateTemplateSource.h"
#include <pybind11/pybind11.h>

void init_GateTemplateSource(py::module &m) {

  py::class_<GateTemplateSource, GateVSource>(m, "GateTemplateSource")
      .def(py::init())
      .def("InitializeUserInfo", &GateTemplateSource::InitializeUserInfo)
      // If needed: add your own class functions that will be accessible from
      // python side.
      ;
}
