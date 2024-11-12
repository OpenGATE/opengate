/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateKineticEnergyFilter.h"
#include "GateVFilter.h"

void init_GateKineticEnergyFilter(py::module &m) {
  py::class_<GateKineticEnergyFilter, GateVFilter>(m, "GateKineticEnergyFilter")
      .def(py::init())
      .def("InitializeUserInput",
           &GateKineticEnergyFilter::InitializeUserInput);
}
