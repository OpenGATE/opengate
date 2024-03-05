/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateTreatmentPlanSourcePB.h"

void init_GateTreatmentPlanSourcePB(py::module &m) {

  py::class_<GateTreatmentPlanSourcePB, GateVSource>(
      m, "GateTreatmentPlanSourcePB")
      .def(py::init())
      .def_readonly("fNumberOfGeneratedEvents",
                    &GateTreatmentPlanSourcePB::fNumberOfGeneratedEvents)
      .def("InitializeUserInfo",
           &GateTreatmentPlanSourcePB::InitializeUserInfo);
}
