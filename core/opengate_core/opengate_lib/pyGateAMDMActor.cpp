/* Copyright (C): OpenGATE Collaboration. See LICENSE.md for LGPL terms. */
#include "GateAMDMActor.h"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

class PyGateAMDMActor : public GateAMDMActor {
public:
  using GateAMDMActor::GateAMDMActor;
  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateAMDMActor, BeginOfRunActionMasterThread,
                      run_id);
  }
  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateAMDMActor, EndOfRunActionMasterThread, run_id);
  }
};

void init_GateAMDMActor(py::module &m) {
  py::class_<GateAMDMActor, PyGateAMDMActor,
             std::unique_ptr<GateAMDMActor, py::nodelete>, GateVActor>(
      m, "GateAMDMActor")
      .def(py::init<py::dict &>())
      .def("BeginOfRunActionMasterThread",
           &GateAMDMActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateAMDMActor::EndOfRunActionMasterThread)
      .def_readwrite("cpp_amdm_restricted_edep_image",
                     &GateAMDMActor::cpp_amdm_restricted_edep_image)
      .def_readwrite("cpp_amdm_delta_image",
                     &GateAMDMActor::cpp_amdm_delta_image)
      .def_readwrite("cpp_amdm_gamma_image",
                     &GateAMDMActor::cpp_amdm_gamma_image)
      .def_readonly("NbOfEvent", &GateAMDMActor::NbOfEvent)
      .def("Lookup", &GateAMDMActor::Lookup, py::arg("charge"),
           py::arg("energy"))
      .def("GetPhysicalVolumeName", &GateAMDMActor::GetPhysicalVolumeName)
      .def("SetPhysicalVolumeName", &GateAMDMActor::SetPhysicalVolumeName);
}
