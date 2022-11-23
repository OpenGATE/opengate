/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateHitsReadoutActor.h"
#include "digitizer/GateDigitizerAdderActor.h"

void init_GateHitsReadoutActor(py::module &m) {

  py::class_<GateHitsReadoutActor,
             std::unique_ptr<GateHitsReadoutActor, py::nodelete>,
             GateDigitizerAdderActor>(m, "GateHitsReadoutActor")
      .def(py::init<py::dict &>())
      .def("SetGroupVolumeDepth", &GateDigitizerAdderActor::SetGroupVolumeDepth)
      .def("SetDiscretizeVolumeDepth",
           &GateHitsReadoutActor::SetDiscretizeVolumeDepth);
}
