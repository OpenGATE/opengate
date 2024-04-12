/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateInfo.h"

void init_GateInfo(py::module &m) {
  py::class_<GateInfo>(m, "GateInfo")
      .def(py::init())
      .def("get_G4MULTITHREADED", &GateInfo::get_G4MULTITHREADED)
      .def("get_G4Version", &GateInfo::get_G4Version)
      .def("get_G4Date", &GateInfo::get_G4Date)
      .def("get_ITKVersion", &GateInfo::get_ITKVersion)
      .def("test", &GateInfo::test)
      .def("get_G4GDML", &GateInfo::get_G4GDML);
}
