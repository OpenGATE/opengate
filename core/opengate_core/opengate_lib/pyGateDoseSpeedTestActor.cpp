/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateDoseSpeedTestActor.h"

void init_GateDoseSpeedTestActor(py::module &m) {
  py::class_<GateDoseSpeedTestActor,
             std::unique_ptr<GateDoseSpeedTestActor, py::nodelete>, GateVActor>(
      m, "GateDoseSpeedTestActor")
      .def(py::init<py::dict &>())
      .def("PrepareStorage", &GateDoseSpeedTestActor::PrepareStorage)
      .def("GetTotalReattemptsAtomicAdd",
           &GateDoseSpeedTestActor::GetTotalReattemptsAtomicAdd)
      .def("GetTotalDepositWrites",
           &GateDoseSpeedTestActor::GetTotalDepositWrites)
      .def_readwrite("cpp_reference_image",
                     &GateDoseSpeedTestActor::cpp_reference_image)
      .def_readwrite("cpp_image", &GateDoseSpeedTestActor::cpp_image)
      .def_readwrite("fPhysicalVolumeName",
                     &GateDoseSpeedTestActor::fPhysicalVolumeName);
}
