/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;
#include "G4VBiasingOperator.hh"
#include "GateOptrSplitComptonScatteringActor.h"

void init_GateOptrSplitComptonScatteringActor(py::module &m) {
  py::class_<
      GateOptrSplitComptonScatteringActor, G4VBiasingOperator, GateVActor,
      std::unique_ptr<GateOptrSplitComptonScatteringActor, py::nodelete>>(
      m, "GateOptrSplitComptonScatteringActor")
      .def(py::init<py::dict &>())
      .def("ConfigureForWorker",
           &GateOptrSplitComptonScatteringActor::ConfigureForWorker)
      .def("GetSplitStats",
           &GateOptrSplitComptonScatteringActor::GetSplitStats);
}
