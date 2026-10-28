/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDepositedChargeActor.h"
#include <pybind11/pybind11.h>

// Trampoline so that the master-thread run callbacks can be overridden on the
// Python side.
class PyGateDepositedChargeActor : public GateDepositedChargeActor {
public:
  using GateDepositedChargeActor::GateDepositedChargeActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateDepositedChargeActor,
                      BeginOfRunActionMasterThread, run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateDepositedChargeActor, EndOfRunActionMasterThread,
                      run_id);
  }
};

void init_GateDepositedChargeActor(py::module &m) {
  py::class_<GateDepositedChargeActor, PyGateDepositedChargeActor,
             std::unique_ptr<GateDepositedChargeActor, py::nodelete>,
             GateVActor>(m, "GateDepositedChargeActor")
      .def(py::init<py::dict &>())
      .def("GetDepositedNominalCharge",
           &GateDepositedChargeActor::GetDepositedNominalCharge)
      .def("GetDepositedDynamicCharge",
           &GateDepositedChargeActor::GetDepositedDynamicCharge)
      .def("GetDepositedNominalChargeSquared",
           &GateDepositedChargeActor::GetDepositedNominalChargeSquared)
      .def("GetDepositedDynamicChargeSquared",
           &GateDepositedChargeActor::GetDepositedDynamicChargeSquared)
      .def("GetNumberOfEvents", &GateDepositedChargeActor::GetNumberOfEvents);
}
