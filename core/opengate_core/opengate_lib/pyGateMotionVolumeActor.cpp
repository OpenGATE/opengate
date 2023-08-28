/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateMotionVolumeActor.h"

void init_GateMotionVolumeActor(py::module &m) {

  py::class_<GateMotionVolumeActor,
             std::unique_ptr<GateMotionVolumeActor, py::nodelete>, GateVActor>(
      m, "GateMotionVolumeActor")
      .def(py::init<py::dict &>())
      .def("SetTranslations", &GateMotionVolumeActor::SetTranslations)
      .def("SetRotations", &GateMotionVolumeActor::SetRotations);
}
