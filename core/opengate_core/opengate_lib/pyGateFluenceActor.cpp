/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateFluenceActor.h"

class PyGateFluenceActor : public GateFluenceActor {
public:
  // Inherit the constructors
  using GateFluenceActor::GateFluenceActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateFluenceActor, BeginOfRunActionMasterThread,
                      run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateFluenceActor, EndOfRunActionMasterThread,
                      run_id);
  }
};

void init_GateFluenceActor(py::module &m) {
  py::class_<GateFluenceActor, PyGateFluenceActor,
             std::unique_ptr<GateFluenceActor, py::nodelete>, GateVActor>(
      m, "GateFluenceActor")
      .def(py::init<py::dict &>())
      .def("BeginOfRunActionMasterThread",
           &GateFluenceActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateFluenceActor::EndOfRunActionMasterThread)
      .def("GetPhysicalVolumeName", &GateFluenceActor::GetPhysicalVolumeName)
      .def("SetPhysicalVolumeName", &GateFluenceActor::SetPhysicalVolumeName)
      .def("GetEnergySquaredFlag", &GateFluenceActor::GetEnergySquaredFlag)
      .def("SetEnergySquaredFlag", &GateFluenceActor::SetEnergySquaredFlag)
      .def("GetEnergyFlag", &GateFluenceActor::GetEnergyFlag)
      .def("SetEnergyFlag", &GateFluenceActor::SetEnergyFlag)
      .def("GetCountsSquaredFlag", &GateFluenceActor::GetCountsSquaredFlag)
      .def("SetCountsSquaredFlag", &GateFluenceActor::SetCountsSquaredFlag)
      .def_readwrite("NbOfEvent", &GateFluenceActor::NbOfEvent)
      .def_readwrite("cpp_counts_image", &GateFluenceActor::cpp_counts_image)
      .def_readwrite("cpp_energy_image", &GateFluenceActor::cpp_energy_image)
      .def_readwrite("cpp_counts_squared_image",&GateFluenceActor::cpp_counts_squared_image)
      .def_readwrite("cpp_energy_squared_image",&GateFluenceActor::cpp_energy_squared_image)
      .def_readwrite("cpp_counts_compton_image", &GateFluenceActor::cpp_counts_compton_image)
      .def_readwrite("cpp_energy_compton_image", &GateFluenceActor::cpp_energy_compton_image)
      .def_readwrite("cpp_counts_squared_compton_image",&GateFluenceActor::cpp_counts_squared_compton_image)
      .def_readwrite("cpp_energy_squared_compton_image",&GateFluenceActor::cpp_energy_squared_compton_image)
      .def_readwrite("cpp_counts_rayleigh_image", &GateFluenceActor::cpp_counts_rayleigh_image)
      .def_readwrite("cpp_energy_rayleigh_image", &GateFluenceActor::cpp_energy_rayleigh_image)
      .def_readwrite("cpp_counts_squared_rayleigh_image",&GateFluenceActor::cpp_counts_squared_rayleigh_image)
      .def_readwrite("cpp_energy_squared_rayleigh_image",&GateFluenceActor::cpp_energy_squared_rayleigh_image)
      .def_readwrite("cpp_counts_secondaries_image", &GateFluenceActor::cpp_counts_secondaries_image)
      .def_readwrite("cpp_energy_secondaries_image", &GateFluenceActor::cpp_energy_secondaries_image)
      .def_readwrite("cpp_counts_squared_secondaries_image",&GateFluenceActor::cpp_counts_squared_secondaries_image)
      .def_readwrite("cpp_energy_squared_secondaries_image",&GateFluenceActor::cpp_energy_squared_secondaries_image)
      .def_readwrite("cpp_counts_primaries_image", &GateFluenceActor::cpp_counts_primaries_image)
      .def_readwrite("cpp_energy_primaries_image", &GateFluenceActor::cpp_energy_primaries_image)
      .def_readwrite("cpp_counts_squared_primaries_image",&GateFluenceActor::cpp_counts_squared_primaries_image)
      .def_readwrite("cpp_energy_squared_primaries_image",&GateFluenceActor::cpp_energy_squared_primaries_image);
}
