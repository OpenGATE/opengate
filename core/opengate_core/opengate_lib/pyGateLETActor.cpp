/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateLETActor.h"

void init_GateLETActor(py::module &m) {
  py::class_<GateLETActor, std::unique_ptr<GateLETActor, py::nodelete>,
             GateVActor>(m, "GateLETActor")
      .def(py::init<py::dict &>())
      .def_readwrite("cpp_numerator_image", &GateLETActor::cpp_numerator_image)
      .def_readwrite("cpp_denominator_image",
                     &GateLETActor::cpp_denominator_image)
      .def_readwrite("fPhysicalVolumeName", &GateLETActor::fPhysicalVolumeName);
}
