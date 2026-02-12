/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateParticleFilter.h"
#include "GateVFilter.h"

void init_GateParticleFilter(py::module &m) {
  py::class_<GateParticleFilter, GateVFilter>(m, "GateParticleFilter")
      .def(py::init())
      .def("InitializeUserInfo", &GateParticleFilter::InitializeUserInfo);
}
