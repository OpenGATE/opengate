/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateVSource.h"

void init_GateVSource(py::module &m) {

  py::class_<GateVSource, std::unique_ptr<GateVSource, py::nodelete>>(
      m, "GateVSource")
      .def(py::init())
      .def("InitializeUserInfo", &GateVSource::InitializeUserInfo)
      .def("SetOrientationAccordingToMotherVolume",
           &GateVSource::SetOrientationAccordingToMotherVolume);
}
