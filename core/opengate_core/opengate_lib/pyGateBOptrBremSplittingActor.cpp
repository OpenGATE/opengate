/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;
#include "G4VBiasingOperator.hh"
#include "GateBOptrBremSplittingActor.h"

void init_GateBOptrBremSplittingActor(py::module &m) {

  py::class_<GateBOptrBremSplittingActor, G4VBiasingOperator, GateVActor,
             std::unique_ptr<GateBOptrBremSplittingActor, py::nodelete>>(
      m, "GateBOptrBremSplittingActor")
      .def(py::init<py::dict &>());
}
