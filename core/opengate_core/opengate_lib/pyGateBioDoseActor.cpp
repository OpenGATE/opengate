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
      .def("InitializeUserInput", &GateBioDoseActor::InitializeUserInput)
      .def("BeginOfRunActionMasterThread",
           &GateBioDoseActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateBioDoseActor::EndOfRunActionMasterThread)
      .def("GetPhysicalVolumeName", &GateBioDoseActor::GetPhysicalVolumeName)
      .def("SetPhysicalVolumeName", &GateBioDoseActor::SetPhysicalVolumeName)
      .def_readwrite("cpp_edep_image", &GateBioDoseActor::fEdepImage)
      .def_readwrite("NbOfEvent", &GateBioDoseActor::fNbOfEvent)
			;
}
