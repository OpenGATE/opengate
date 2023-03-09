/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateGenericSource.h"

void init_GateGenericSource(py::module &m) {

  py::class_<GateGenericSource, GateVSource>(m, "GateGenericSource")
      .def(py::init())
      .def_readonly("fNumberOfGeneratedEvents",
                    &GateGenericSource::fNumberOfGeneratedEvents)
      .def("InitializeUserInfo", &GateGenericSource::InitializeUserInfo)
      .def("SetEnergyCDF", &GateGenericSource::SetEnergyCDF)
      .def("SetProbabilityCDF", &GateGenericSource::SetProbabilityCDF)
      .def_readonly("fTotalSkippedEvents",
                    &GateGenericSource::fTotalSkippedEvents)
      .def_readonly("fTotalZeroEvents", &GateGenericSource::fTotalZeroEvents)
      .def("SetTAC", &GateGenericSource::SetTAC);
}
