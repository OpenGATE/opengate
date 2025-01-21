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
      .def_readwrite("cpp_image", &GateVoxelizedPromptGammaTLEActor::cpp_image);
}
