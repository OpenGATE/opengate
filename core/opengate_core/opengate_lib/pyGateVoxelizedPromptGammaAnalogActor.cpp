/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateVoxelizedPromptGammaAnalogActor.h"

class PyGateVoxelizedPromptGammaAnalogActor
    : public GateVoxelizedPromptGammaAnalogActor {
public:
  // Inherit the constructors
  using GateVoxelizedPromptGammaAnalogActor::
      GateVoxelizedPromptGammaAnalogActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateVoxelizedPromptGammaAnalogActor,
                      BeginOfRunActionMasterThread, run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateVoxelizedPromptGammaAnalogActor,
                      EndOfRunActionMasterThread, run_id);
  }
};

void init_GateVoxelizedPromptGammaAnalogActor(py::module &m) {
  py::class_<GateVoxelizedPromptGammaAnalogActor,
             PyGateVoxelizedPromptGammaAnalogActor,
             std::unique_ptr<GateVoxelizedPromptGammaAnalogActor, py::nodelete>,
             GateVActor>(m, "GateVoxelizedPromptGammaAnalogActor")
      .def(py::init<py::dict &>())
      .def("InitializeUserInfo",
           &GateVoxelizedPromptGammaAnalogActor::InitializeUserInfo)
      .def("BeginOfRunActionMasterThread",
           &GateVoxelizedPromptGammaAnalogActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateVoxelizedPromptGammaAnalogActor::EndOfRunActionMasterThread)
      .def("SetPhysicalVolumeName",
           &GateVoxelizedPromptGammaAnalogActor::SetPhysicalVolumeName)
      .def("GetPhysicalVolumeName",
           &GateVoxelizedPromptGammaAnalogActor::GetPhysicalVolumeName)

      .def("SetProtonTimeFlag",
           &GateVoxelizedPromptGammaAnalogActor::SetProtonTimeFlag)
      .def("GetProtonTimeFlag",
           &GateVoxelizedPromptGammaAnalogActor::GetProtonTimeFlag)

      .def("SetProtonEnergyFlag",
           &GateVoxelizedPromptGammaAnalogActor::SetProtonEnergyFlag)
      .def("GetProtonEnergyFlag",
           &GateVoxelizedPromptGammaAnalogActor::GetProtonEnergyFlag)

      .def("SetNeutronEnergyFlag",
           &GateVoxelizedPromptGammaAnalogActor::SetNeutronEnergyFlag)
      .def("GetNeutronEnergyFlag",
           &GateVoxelizedPromptGammaAnalogActor::GetNeutronEnergyFlag)

      .def("SetNeutronTimeFlag",
           &GateVoxelizedPromptGammaAnalogActor::SetNeutronTimeFlag)
      .def("GetNeutronTimeFlag",
           &GateVoxelizedPromptGammaAnalogActor::GetNeutronTimeFlag)

      .def_readwrite("fPhysicalVolumeName",
                     &GateVoxelizedPromptGammaAnalogActor::fPhysicalVolumeName)
      .def_readwrite(
          "cpp_tof_neutron_image",
          &GateVoxelizedPromptGammaAnalogActor::cpp_tof_neutron_image)
      .def_readwrite("cpp_tof_proton_image",
                     &GateVoxelizedPromptGammaAnalogActor::cpp_tof_proton_image)
      .def_readwrite("cpp_E_neutron_image",
                     &GateVoxelizedPromptGammaAnalogActor::cpp_E_neutron_image)
      .def_readwrite("cpp_E_proton_image",
                     &GateVoxelizedPromptGammaAnalogActor::cpp_E_proton_image);
}
