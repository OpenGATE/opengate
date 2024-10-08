/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateDigitizerProjectionActor.h"

void init_GateDigitizerProjectionActor(py::module &m) {

  py::class_<GateDigitizerProjectionActor,
             std::unique_ptr<GateDigitizerProjectionActor, py::nodelete>,
             GateVActor>(m, "GateDigitizerProjectionActor")
      .def(py::init<py::dict &>())
      .def_readwrite("fImage", &GateDigitizerProjectionActor::fImage)
      .def("SetPhysicalVolumeName",
           &GateDigitizerProjectionActor::SetPhysicalVolumeName);
}
