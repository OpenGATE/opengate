/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;
#include "G4VBiasingOperator.hh"
#include "GateOptrComptPseudoTransportationActor.h"

void init_GateOptrComptPseudoTransportationActor(py::module &m) {

  py::class_<
      GateOptrComptPseudoTransportationActor, G4VBiasingOperator, GateVActor,
      std::unique_ptr<GateOptrComptPseudoTransportationActor, py::nodelete>>(
      m, "GateOptrComptPseudoTransportationActor")
      .def(py::init<py::dict &>());
}
