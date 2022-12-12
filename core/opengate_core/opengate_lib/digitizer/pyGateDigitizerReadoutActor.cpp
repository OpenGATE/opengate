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
#include "GateDigitizerReadoutActor.h"

void init_GateDigitizerReadoutActor(py::module &m) {

  py::class_<GateDigitizerReadoutActor,
             std::unique_ptr<GateDigitizerReadoutActor, py::nodelete>,
             GateDigitizerAdderActor>(m, "GateDigitizerReadoutActor")
      .def(py::init<py::dict &>())
      .def("SetGroupVolumeDepth", &GateDigitizerAdderActor::SetGroupVolumeDepth)
      .def("GetIgnoredHitsCount",
           &GateDigitizerReadoutActor::GetIgnoredHitsCount)
      .def("SetDiscretizeVolumeDepth",
           &GateDigitizerReadoutActor::SetDiscretizeVolumeDepth);
}
