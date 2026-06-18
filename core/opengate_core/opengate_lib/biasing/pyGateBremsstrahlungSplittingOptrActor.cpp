/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

#include "../GateVActor.h"
#include "GateBremsstrahlungSplittingOptrActor.h"
#include <G4VBiasingOperator.hh>

void init_GateBOptrBremSplittingActor(py::module &m) {
  py::class_<GateBremsstrahlungSplittingOptrActor, G4VBiasingOperator,
             GateVActor>(m, "GateBremsstrahlungSplittingOptrActor")
      .def(py::init<py::dict &>())
      .def("ClearOperators",
           &GateBremsstrahlungSplittingOptrActor::ClearOperators);
}
