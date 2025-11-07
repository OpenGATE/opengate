/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateARFActor.h"

class PyGateARFActor : public GateARFActor {
public:
  // Inherit the constructors
  using GateARFActor::GateARFActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateARFActor, BeginOfRunActionMasterThread, run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateARFActor, EndOfRunActionMasterThread, run_id);
  }
};

void init_GateARFActor(py::module &m) {
  py::class_<GateARFActor, PyGateARFActor,
             std::unique_ptr<GateARFActor, py::nodelete>, GateVActor>(
      m, "GateARFActor")
      .def(py::init<py::dict &>())
      .def("BeginOfRunActionMasterThread",
           &GateARFActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateARFActor::EndOfRunActionMasterThread)
      .def("SetARFFunction", &GateARFActor::SetARFFunction)
      .def("GetCurrentNumberOfHits", &GateARFActor::GetCurrentNumberOfHits)
      .def("GetCurrentRunId", &GateARFActor::GetCurrentRunId)
      .def("GetEnergy", &GateARFActor::GetEnergy)
      .def("GetPositionX", &GateARFActor::GetPositionX)
      .def("GetPositionY", &GateARFActor::GetPositionY)
      .def("GetDirectionX", &GateARFActor::GetDirectionX)
      .def("GetDirectionY", &GateARFActor::GetDirectionY)
      .def("GetDirectionZ", &GateARFActor::GetDirectionZ)
      .def("GetWeights", &GateARFActor::GetWeights);
}
