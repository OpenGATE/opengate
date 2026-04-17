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
      .def("GetPhysicalVolumeName",
           &GateClusterDoseActor::GetPhysicalVolumeName)
      .def("SetPhysicalVolumeName",
           &GateClusterDoseActor::SetPhysicalVolumeName)
      .def_readwrite("NbOfEvent", &GateClusterDoseActor::NbOfEvent)
      .def_readwrite("cpp_cluster_dose_image",
                     &GateClusterDoseActor::cpp_cluster_dose_image);
}
