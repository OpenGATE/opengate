/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateProductionAndStoppingActor.h"

class PyGateProductionAndStoppingActor : public GateProductionAndStoppingActor {
public:
  // Inherit the constructors
  using GateProductionAndStoppingActor::GateProductionAndStoppingActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateProductionAndStoppingActor,
                      BeginOfRunActionMasterThread, run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateProductionAndStoppingActor,
                      EndOfRunActionMasterThread, run_id);
  }
};

void init_GateProductionAndStoppingActor(py::module &m) {
  py::class_<GateProductionAndStoppingActor, PyGateProductionAndStoppingActor,
             std::unique_ptr<GateProductionAndStoppingActor, py::nodelete>,
             GateVActor>(m, "GateProductionAndStoppingActor")
      .def(py::init<py::dict &>())
      .def("BeginOfRunActionMasterThread",
           &GateProductionAndStoppingActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateProductionAndStoppingActor::EndOfRunActionMasterThread)
      .def_readwrite("cpp_value_image",
                     &GateProductionAndStoppingActor::cpp_value_image)
      .def_readwrite("NbOfEvent", &GateProductionAndStoppingActor::NbOfEvent)
      .def("GetPhysicalVolumeName",
           &GateProductionAndStoppingActor::GetPhysicalVolumeName)
      .def("SetPhysicalVolumeName",
           &GateProductionAndStoppingActor::SetPhysicalVolumeName);
}
