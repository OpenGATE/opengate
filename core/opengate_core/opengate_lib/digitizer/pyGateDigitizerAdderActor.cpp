/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateDigitizerAdderActor.h"

void init_GateHitsAdderActor(py::module &m) {

  py::class_<GateDigitizerAdderActor,
             std::unique_ptr<GateDigitizerAdderActor, py::nodelete>,
             GateVDigitizerWithOutputActor>(m, "GateDigitizerAdderActor")
      .def(py::init<py::dict &>())
      .def("SetGroupVolumeDepth",
           &GateDigitizerAdderActor::SetGroupVolumeDepth);
}
