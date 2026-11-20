/* Copyright (C): OpenGATE Collaboration. See LICENSE.md for LGPL terms. */
#include "GateAMDMActor.h"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

/** Forward master callbacks to the Python wrapper that owns the output
 * lifecycle. */
class PyGateAMDMActor : public GateAMDMActor {
public:
  using GateAMDMActor::GateAMDMActor;
  /** Dispatch run allocation/attachment to a Python override when present. */
  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateAMDMActor, BeginOfRunActionMasterThread,
                      run_id);
  }
  /** Dispatch completed-run copying/merging to a Python override when present.
   */
  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateAMDMActor, EndOfRunActionMasterThread, run_id);
  }
};

/** Register the actor, image buffers, master callbacks and lookup inspection
 * API. */
void init_GateAMDMActor(py::module &m) {
  py::class_<GateAMDMActor, PyGateAMDMActor,
             std::unique_ptr<GateAMDMActor, py::nodelete>, GateVActor>(
      m, "GateAMDMActor",
      "C++ AMDM scorer with thread-safe raw image accumulation.")
      .def(py::init<py::dict &>(),
           "Construct the scorer from Python user information.")
      .def("BeginOfRunActionMasterThread",
           &GateAMDMActor::BeginOfRunActionMasterThread,
           "Reset event counts and attach fresh raw images to the current "
           "volume pose.")
      .def("EndOfRunActionMasterThread",
           &GateAMDMActor::EndOfRunActionMasterThread,
           "Complete a master-thread run; Python overrides copy and merge raw "
           "outputs.")
      .def_readwrite("cpp_amdm_restricted_edep_image",
                     &GateAMDMActor::cpp_amdm_restricted_edep_image)
      .def_readwrite("cpp_amdm_delta_image",
                     &GateAMDMActor::cpp_amdm_delta_image)
      .def_readwrite("cpp_amdm_gamma_image",
                     &GateAMDMActor::cpp_amdm_gamma_image)
      .def_readonly("NbOfEvent", &GateAMDMActor::NbOfEvent)
      .def("Lookup", &GateAMDMActor::Lookup, py::arg("charge"),
           py::arg("energy"),
           "Return interpolated gamma then delta bins for charge and energy in "
           "MeV/n; "
           "clamp endpoints and return an empty list for missing charges or "
           "NaN.")
      .def("GetPhysicalVolumeName", &GateAMDMActor::GetPhysicalVolumeName,
           "Return the resolved physical-volume name used for scoring-grid "
           "attachment.")
      .def("SetPhysicalVolumeName", &GateAMDMActor::SetPhysicalVolumeName,
           "Set the resolved physical-volume name used for scoring-grid "
           "attachment.");
}
