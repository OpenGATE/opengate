/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateVoxelizedPromptGammaTLEActor.h"

class PyGateVoxelizedPromptGammaTLEActor
    : public GateVoxelizedPromptGammaTLEActor {
public:
  // Inherit the constructors
  using GateVoxelizedPromptGammaTLEActor::GateVoxelizedPromptGammaTLEActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateVoxelizedPromptGammaTLEActor,
                      BeginOfRunActionMasterThread, run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateVoxelizedPromptGammaTLEActor,
                      EndOfRunActionMasterThread, run_id);
  }
};

void init_GateVoxelizedPromptGammaTLEActor(py::module &m) {
  py::class_<GateVoxelizedPromptGammaTLEActor,
             PyGateVoxelizedPromptGammaTLEActor,
             std::unique_ptr<GateVoxelizedPromptGammaTLEActor, py::nodelete>,
             GateVActor>(m, "GateVoxelizedPromptGammaTLEActor")
      .def(py::init<py::dict &>())
      .def("InitializeUserInfo",
           &GateVoxelizedPromptGammaTLEActor::InitializeUserInfo)
      .def("BeginOfRunActionMasterThread",
           &GateVoxelizedPromptGammaTLEActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateVoxelizedPromptGammaTLEActor::EndOfRunActionMasterThread)
      .def("SetPhysicalVolumeName",
           &GateVoxelizedPromptGammaTLEActor::SetPhysicalVolumeName)
      .def("GetPhysicalVolumeName",
           &GateVoxelizedPromptGammaTLEActor::GetPhysicalVolumeName)
      .def("SetVector", &GateVoxelizedPromptGammaTLEActor::SetVector)
      .def("SetProtonTimeFlag",
           &GateVoxelizedPromptGammaTLEActor::SetProtonTimeFlag)
      .def("GetProtonTimeFlag",
           &GateVoxelizedPromptGammaTLEActor::GetProtonTimeFlag)

      .def("SetProtonEnergyFlag",
           &GateVoxelizedPromptGammaTLEActor::SetProtonEnergyFlag)
      .def("GetProtonEnergyFlag",
           &GateVoxelizedPromptGammaTLEActor::GetProtonEnergyFlag)

      .def("SetNeutronEnergyFlag",
           &GateVoxelizedPromptGammaTLEActor::SetNeutronEnergyFlag)
      .def("GetNeutronEnergyFlag",
           &GateVoxelizedPromptGammaTLEActor::GetNeutronEnergyFlag)

      .def("SetNeutronTimeFlag",
           &GateVoxelizedPromptGammaTLEActor::SetNeutronTimeFlag)
      .def("GetNeutronTimeFlag",
           &GateVoxelizedPromptGammaTLEActor::GetNeutronTimeFlag)

      .def_readwrite("fPhysicalVolumeName",
                     &GateVoxelizedPromptGammaTLEActor::fPhysicalVolumeName)
      .def_readwrite("cpp_tof_neutron_image",
                     &GateVoxelizedPromptGammaTLEActor::cpp_tof_neutron_image)
      .def_readwrite("cpp_tof_proton_image",
                     &GateVoxelizedPromptGammaTLEActor::cpp_tof_proton_image)
      .def_readwrite("cpp_E_neutron_image",
                     &GateVoxelizedPromptGammaTLEActor::cpp_E_neutron_image)
      .def_readwrite("cpp_E_proton_image",
                     &GateVoxelizedPromptGammaTLEActor::cpp_E_proton_image);
}
