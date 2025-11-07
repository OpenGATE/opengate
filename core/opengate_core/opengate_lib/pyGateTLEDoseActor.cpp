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
#include "GateTLEDoseActor.h"

class PyGateTLEDoseActor : public GateTLEDoseActor {
public:
  // Inherit the constructors
  using GateTLEDoseActor::GateTLEDoseActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateTLEDoseActor, BeginOfRunActionMasterThread,
                      run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateTLEDoseActor, EndOfRunActionMasterThread,
                      run_id);
  }
};

void init_GateTLEDoseActor(py::module &m) {
  py::class_<GateTLEDoseActor, PyGateTLEDoseActor,
             std::unique_ptr<GateTLEDoseActor, py::nodelete>, GateDoseActor>(
      m, "GateTLEDoseActor")
      .def(py::init<py::dict &>())
      .def("InitializeUserInfo", &GateTLEDoseActor::InitializeUserInfo)
      .def("BeginOfRunActionMasterThread",
           &GateTLEDoseActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateTLEDoseActor::EndOfRunActionMasterThread)
      .def("GetEdepSquaredFlag", &GateTLEDoseActor::GetEdepSquaredFlag)
      .def("SetEdepSquaredFlag", &GateTLEDoseActor::SetEdepSquaredFlag)
      .def("GetDoseFlag", &GateTLEDoseActor::GetDoseFlag)
      .def("SetDoseFlag", &GateTLEDoseActor::SetDoseFlag)
      .def("GetDoseSquaredFlag", &GateTLEDoseActor::GetDoseSquaredFlag)
      .def("SetDoseSquaredFlag", &GateTLEDoseActor::SetDoseSquaredFlag)
      .def("GetToWaterFlag", &GateTLEDoseActor::GetToWaterFlag)
      .def("SetToWaterFlag", &GateTLEDoseActor::SetToWaterFlag)
      .def("GetCountsFlag", &GateTLEDoseActor::GetCountsFlag)
      .def("SetCountsFlag", &GateTLEDoseActor::SetCountsFlag)
      .def("GetPhysicalVolumeName", &GateTLEDoseActor::GetPhysicalVolumeName)
      .def("SetPhysicalVolumeName", &GateTLEDoseActor::SetPhysicalVolumeName)
      .def_readwrite("NbOfEvent", &GateTLEDoseActor::fNbOfEvent)
      .def_readwrite("cpp_edep_image", &GateTLEDoseActor::cpp_edep_image)
      .def_readwrite("cpp_edep_squared_image",
                     &GateTLEDoseActor::cpp_edep_squared_image)
      .def_readwrite("cpp_dose_image", &GateTLEDoseActor::cpp_dose_image)
      .def_readwrite("cpp_dose_squared_image",
                     &GateTLEDoseActor::cpp_dose_squared_image)
      .def_readwrite("cpp_density_image", &GateTLEDoseActor::cpp_density_image)
      .def_readwrite("cpp_counts_image", &GateTLEDoseActor::cpp_counts_image)
      .def_readwrite("fPhysicalVolumeName",
                     &GateTLEDoseActor::fPhysicalVolumeName);
}
