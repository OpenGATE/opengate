/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateDoseActor.h"

class PyGateDoseActor : public GateDoseActor {
public:
  // Inherit the constructors
  using GateDoseActor::GateDoseActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateDoseActor, BeginOfRunActionMasterThread,
                      run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateDoseActor, EndOfRunActionMasterThread, run_id);
  }
};

void init_GateDoseActor(py::module &m) {
  py::class_<GateDoseActor, PyGateDoseActor,
             std::unique_ptr<GateDoseActor, py::nodelete>, GateVActor>(
      m, "GateDoseActor")
      .def(py::init<py::dict &>())
      .def("InitializeUserInput", &GateDoseActor::InitializeUserInput)
      .def("BeginOfRunActionMasterThread",
           &GateDoseActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateDoseActor::EndOfRunActionMasterThread)
      .def("GetEdepSquaredFlag", &GateDoseActor::GetEdepSquaredFlag)
      .def("SetEdepSquaredFlag", &GateDoseActor::SetEdepSquaredFlag)
      .def("GetDoseFlag", &GateDoseActor::GetDoseFlag)
      .def("SetDoseFlag", &GateDoseActor::SetDoseFlag)
      .def("GetDoseSquaredFlag", &GateDoseActor::GetDoseSquaredFlag)
      .def("SetDoseSquaredFlag", &GateDoseActor::SetDoseSquaredFlag)
      .def("GetToWaterFlag", &GateDoseActor::GetToWaterFlag)
      .def("SetToWaterFlag", &GateDoseActor::SetToWaterFlag)
      .def("GetCountsFlag", &GateDoseActor::GetCountsFlag)
      .def("SetCountsFlag", &GateDoseActor::SetCountsFlag)
      .def("SetUncertaintyGoal", &GateDoseActor::SetUncertaintyGoal)
      .def("SetThreshEdepPerc", &GateDoseActor::SetThreshEdepPerc)
      .def("SetOvershoot", &GateDoseActor::SetOvershoot)
      .def("SetNbEventsFirstCheck", &GateDoseActor::SetNbEventsFirstCheck)
      .def("GetPhysicalVolumeName", &GateDoseActor::GetPhysicalVolumeName)
      .def("SetPhysicalVolumeName", &GateDoseActor::SetPhysicalVolumeName)
      .def_readwrite("NbOfEvent", &GateDoseActor::NbOfEvent)
      .def_readwrite("cpp_edep_image", &GateDoseActor::cpp_edep_image)
      .def_readwrite("cpp_edep_squared_image",
                     &GateDoseActor::cpp_edep_squared_image)
      .def_readwrite("cpp_dose_image", &GateDoseActor::cpp_dose_image)
      .def_readwrite("cpp_dose_squared_image",
                     &GateDoseActor::cpp_dose_squared_image)
      .def_readwrite("cpp_density_image", &GateDoseActor::cpp_density_image)
      .def_readwrite("cpp_counts_image", &GateDoseActor::cpp_counts_image)
      .def_readwrite("fPhysicalVolumeName",
                     &GateDoseActor::fPhysicalVolumeName);
}
