/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateEmCalculatorActor.h"

void init_GateEmCalculatorActor(py::module &m) {

  py::class_<GateEmCalculatorActor, GateVActor>(m, "GateEmCalculatorActor")
      .def(py::init<py::dict &>())
      .def("CalculateElectronicdEdX", &GateEmCalculatorActor::CalculateElectronicdEdX);
}
