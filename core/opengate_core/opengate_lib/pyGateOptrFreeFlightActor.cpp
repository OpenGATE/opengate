/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;
#include "G4VBiasingOperator.hh"
#include "GateOptrFreeFlightActor.h"

void init_GateOptrFreeFlightActor(py::module &m) {

  py::class_<GateOptrFreeFlightActor, G4VBiasingOperator, GateVActor,
             std::unique_ptr<GateOptrFreeFlightActor, py::nodelete>>(
      m, "GateOptrFreeFlightActor")
      .def(py::init<py::dict &>())
      .def("ConfigureForWorker", &GateOptrFreeFlightActor::ConfigureForWorker);
}
