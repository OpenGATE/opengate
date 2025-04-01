/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "GateBioDoseActor.h"

namespace py = pybind11;

class PyGateBioDoseActor : public GateBioDoseActor {
public:
  using GateBioDoseActor::GateBioDoseActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateBioDoseActor, BeginOfRunActionMasterThread,
                      run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateBioDoseActor, EndOfRunActionMasterThread,
                      run_id);
  }
};

void init_GateBioDoseActor(py::module &m) {
  py::class_<GateBioDoseActor, PyGateBioDoseActor,
             std::unique_ptr<GateBioDoseActor, py::nodelete>,
             GateVActor>(m, "GateBioDoseActor")
      .def(py::init<py::dict &>())
      .def("InitializeUserInfo", &GateBioDoseActor::InitializeUserInfo)
      .def("BeginOfRunActionMasterThread",
           &GateBioDoseActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateBioDoseActor::EndOfRunActionMasterThread)
      .def("GetPhysicalVolumeName", &GateBioDoseActor::GetPhysicalVolumeName)
      .def("SetPhysicalVolumeName", &GateBioDoseActor::SetPhysicalVolumeName)
      .def("GetVoxelIndicesAsVector", &GateBioDoseActor::GetVoxelIndicesAsVector)
      .def_readwrite("cpp_hit_event_count_image", &GateBioDoseActor::fHitEventCountImage)
      .def_readwrite("cpp_edep_image", &GateBioDoseActor::fEdepImage)
      .def_readwrite("cpp_dose_image", &GateBioDoseActor::fDoseImage)
      .def_readwrite("cpp_alphamix_image", &GateBioDoseActor::fAlphaMixImage)
      .def_readwrite("cpp_sqrtbetamix_image", &GateBioDoseActor::fSqrtBetaMixImage)
      .def_readwrite("cpp_alphamix_dose_image", &GateBioDoseActor::fAlphaMixDoseImage)
      .def_readwrite("cpp_sqrtbetamix_dose_image", &GateBioDoseActor::fSqrtBetaMixDoseImage)
      .def_readwrite("cpp_sum_alphamix_image", &GateBioDoseActor::fSumAlphaMixImage)
      .def_readwrite("cpp_sum_sqrtbetamix_image", &GateBioDoseActor::fSumSqrtBetaMixImage)
      .def_readwrite("cpp_sum_alphamix_dose_image", &GateBioDoseActor::fSumAlphaMixDoseImage)
      .def_readwrite("cpp_sum_sqrtbetamix_dose_image", &GateBioDoseActor::fSumSqrtBetaMixDoseImage)
      .def_readwrite("NbOfEvent", &GateBioDoseActor::fNbOfEvent)
      ;
}
