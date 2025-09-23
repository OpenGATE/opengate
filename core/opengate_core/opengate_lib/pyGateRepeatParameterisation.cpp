/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4VPVParameterisation.hh"
#include "GateRepeatParameterisation.h"

void init_GateRepeatParameterisation(py::module &m) {

  py::class_<GateRepeatParameterisation, G4VPVParameterisation>(
      m, "GateRepeatParameterisation")
      .def(py::init<>())
      .def("SetUserInfo", &GateRepeatParameterisation::SetUserInfo)
      .def("ComputeTransformation",
           &GateRepeatParameterisation::ComputeTransformation);
}
