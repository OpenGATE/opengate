/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateFluenceActor.h"

void init_GateFluenceActor(py::module &m) {
  py::class_<GateFluenceActor, std::unique_ptr<GateFluenceActor, py::nodelete>,
             GateVActor>(m, "GateFluenceActor")
      .def(py::init<py::dict &>())
      .def_readwrite("cpp_fluence_image", &GateFluenceActor::cpp_fluence_image)
      .def_readwrite("fPhysicalVolumeName",
                     &GateFluenceActor::fPhysicalVolumeName);
}
