/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;
#include "../GateVActor.h"
#include "G4VBiasingOperator.hh"
#include "GateBremsstrahlungSplittingOptrActor.h"

void init_GateBOptrBremSplittingActor(py::module &m) {

  py::class_<
      GateBremsstrahlungSplittingOptrActor, G4VBiasingOperator, GateVActor,
      std::unique_ptr<GateBremsstrahlungSplittingOptrActor, py::nodelete>>(
      m, "GateBremsstrahlungSplittingOptrActor")
      .def(py::init<py::dict &>());
}
