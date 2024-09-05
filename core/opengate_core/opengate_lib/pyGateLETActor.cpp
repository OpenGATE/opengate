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

class PyGateLETActor : public GateLETActor {
public:
  // Inherit the constructors
  using GateLETActor::GateLETActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateLETActor, BeginOfRunActionMasterThread, run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateLETActor, EndOfRunActionMasterThread, run_id);
  }
};

void init_GateLETActor(py::module &m) {
  py::class_<GateLETActor, PyGateLETActor,
             std::unique_ptr<GateLETActor, py::nodelete>, GateVActor>(
      m, "GateLETActor")
      .def(py::init<py::dict &>())
      .def("BeginOfRunActionMasterThread",
           &GateLETActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateLETActor::EndOfRunActionMasterThread)
      .def_readwrite("cpp_numerator_image", &GateLETActor::cpp_numerator_image)
      .def_readwrite("cpp_denominator_image",
                     &GateLETActor::cpp_denominator_image)
      .def_readwrite("NbOfEvent", &GateLETActor::NbOfEvent)
      .def("GetPhysicalVolumeName", &GateLETActor::GetPhysicalVolumeName)
      .def("SetPhysicalVolumeName", &GateLETActor::SetPhysicalVolumeName);
  //      .def_readwrite("fPhysicalVolumeName",
  //      &GateLETActor::fPhysicalVolumeName);
}
