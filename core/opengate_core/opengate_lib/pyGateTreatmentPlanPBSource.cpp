/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateTreatmentPlanPBSource.h"

void init_GateTreatmentPlanPBSource(py::module &m) {

  py::class_<GateTreatmentPlanPBSource, GateVSource>(
      m, "GateTreatmentPlanPBSource")
      .def(py::init())
      .def_readonly("fNumberOfGeneratedEvents",
                    &GateTreatmentPlanPBSource::fNumberOfGeneratedEvents)
      .def("InitializeUserInfo",
           &GateTreatmentPlanPBSource::InitializeUserInfo);
}
