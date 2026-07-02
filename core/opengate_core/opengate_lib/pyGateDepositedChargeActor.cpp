/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDepositedChargeActor.h"
#include <pybind11/pybind11.h>

void init_GateDepositedChargeActor(py::module &m) {
  py::class_<GateDepositedChargeActor,
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
