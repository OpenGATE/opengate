/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateClusterDoseActor.h"

class PyGateClusterDoseActor : public GateClusterDoseActor {
public:
  using GateClusterDoseActor::GateClusterDoseActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateClusterDoseActor, BeginOfRunActionMasterThread,
                      run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateClusterDoseActor, EndOfRunActionMasterThread,
                      run_id);
  }
};

void init_GateClusterDoseActor(py::module &m) {
  py::class_<GateClusterDoseActor, PyGateClusterDoseActor,
             std::unique_ptr<GateClusterDoseActor, py::nodelete>, GateVActor>(
      m, "GateClusterDoseActor")
      .def(py::init<py::dict &>())
      .def("InitializeUserInfo", &GateClusterDoseActor::InitializeUserInfo)
      .def("BeginOfRunActionMasterThread",
           &GateClusterDoseActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateClusterDoseActor::EndOfRunActionMasterThread)
      .def("GetEdepSquaredFlag", &GateClusterDoseActor::GetEdepSquaredFlag)
      .def("SetEdepSquaredFlag", &GateClusterDoseActor::SetEdepSquaredFlag)
      .def("GetDoseFlag", &GateClusterDoseActor::GetDoseFlag)
      .def("SetDoseFlag", &GateClusterDoseActor::SetDoseFlag)
      .def("GetDoseSquaredFlag", &GateClusterDoseActor::GetDoseSquaredFlag)
      .def("SetDoseSquaredFlag", &GateClusterDoseActor::SetDoseSquaredFlag)
      .def("GetScoreInMaterial", &GateClusterDoseActor::GetScoreInMaterial)
      .def("SetScoreInMaterial", &GateClusterDoseActor::SetScoreInMaterial)
      .def("GetFastSPRCalculationFlag",
           &GateClusterDoseActor::GetFastSPRCalculationFlag)
      .def("SetFastSPRCalculationFlag",
           &GateClusterDoseActor::SetFastSPRCalculationFlag)
      .def("GetReferenceEnergySPR",
           &GateClusterDoseActor::GetReferenceEnergySPR)
      .def("SetReferenceEnergySPR",
           &GateClusterDoseActor::SetReferenceEnergySPR)
      .def("GetTransitionEnergySPR",
           &GateClusterDoseActor::GetTransitionEnergySPR)
      .def("SetTransitionEnergySPR",
           &GateClusterDoseActor::SetTransitionEnergySPR)
      .def("GetCountsFlag", &GateClusterDoseActor::GetCountsFlag)
      .def("SetCountsFlag", &GateClusterDoseActor::SetCountsFlag)
      .def("SetUncertaintyGoal", &GateClusterDoseActor::SetUncertaintyGoal)
      .def("SetThreshEdepPerc", &GateClusterDoseActor::SetThreshEdepPerc)
      .def("SetOvershoot", &GateClusterDoseActor::SetOvershoot)
      .def("SetNbEventsFirstCheck",
           &GateClusterDoseActor::SetNbEventsFirstCheck)
      .def("GetPhysicalVolumeName",
           &GateClusterDoseActor::GetPhysicalVolumeName)
      .def("SetPhysicalVolumeName",
           &GateClusterDoseActor::SetPhysicalVolumeName)
      .def_readwrite("NbOfEvent", &GateClusterDoseActor::fNbOfEvent)
      .def_readwrite("cpp_edep_image", &GateClusterDoseActor::cpp_edep_image)
      .def_readwrite("cpp_edep_squared_image",
                     &GateClusterDoseActor::cpp_edep_squared_image)
      .def_readwrite("cpp_dose_image", &GateClusterDoseActor::cpp_dose_image)
      .def_readwrite("cpp_dose_squared_image",
                     &GateClusterDoseActor::cpp_dose_squared_image)
      .def_readwrite("cpp_density_image",
                     &GateClusterDoseActor::cpp_density_image)
      .def_readwrite("cpp_counts_image",
                     &GateClusterDoseActor::cpp_counts_image)
      .def_readwrite("fPhysicalVolumeName",
                     &GateClusterDoseActor::fPhysicalVolumeName);
}
