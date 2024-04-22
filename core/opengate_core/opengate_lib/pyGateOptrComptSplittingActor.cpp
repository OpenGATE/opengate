/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;
#include "G4VBiasingOperator.hh"
#include "GateOptrComptSplittingActor.h"

void init_GateOptrComptSplittingActor(py::module &m) {

  py::class_<GateOptrComptSplittingActor, G4VBiasingOperator, GateVActor,
             std::unique_ptr<GateOptrComptSplittingActor, py::nodelete>>(
      m, "GateOptrComptSplittingActor")
      .def(py::init<py::dict &>());
}
