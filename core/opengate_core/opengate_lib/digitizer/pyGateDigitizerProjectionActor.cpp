/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerProjectionActor.h"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

class PyDigitizerProjectionActor : public GateDigitizerProjectionActor {
public:
  // Inherit the constructors
  using GateDigitizerProjectionActor::GateDigitizerProjectionActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateDigitizerProjectionActor,
                      BeginOfRunActionMasterThread, run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateDigitizerProjectionActor,
                      EndOfRunActionMasterThread, run_id);
  }
};

void init_GateDigitizerProjectionActor(py::module &m) {

  py::class_<GateDigitizerProjectionActor,
             std::unique_ptr<GateDigitizerProjectionActor, py::nodelete>,
             GateVActor>(m, "GateDigitizerProjectionActor")
      .def(py::init<py::dict &>())
      .def("BeginOfRunActionMasterThread",
           &GateDigitizerProjectionActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateDigitizerProjectionActor::EndOfRunActionMasterThread)
      .def_readwrite("fImage", &GateDigitizerProjectionActor::fImage)
      .def_readwrite("fSquaredImage",
                     &GateDigitizerProjectionActor::fSquaredImage)
      .def("EnableSquaredImage",
           &GateDigitizerProjectionActor::EnableSquaredImage)
      .def("SetPhysicalVolumeName",
           &GateDigitizerProjectionActor::SetPhysicalVolumeName);
}
