/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateHitsAdderActor.h"
#include "GateHitsReadoutActor.h"

void init_GateHitsReadoutActor(py::module &m) {

  py::class_<GateHitsReadoutActor,
             std::unique_ptr<GateHitsReadoutActor, py::nodelete>,
             GateHitsAdderActor>(m, "GateHitsReadoutActor")
      .def(py::init<py::dict &>())
      .def("SetGroupVolumeDepth", &GateHitsAdderActor::SetGroupVolumeDepth)
      .def("SetDiscretizeVolumeDepth",
           &GateHitsReadoutActor::SetDiscretizeVolumeDepth);
}
