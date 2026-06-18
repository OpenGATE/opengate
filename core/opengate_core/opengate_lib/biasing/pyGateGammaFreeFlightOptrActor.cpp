/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateGammaFreeFlightOptrActor.h"
#include <G4VBiasingOperator.hh>
#include <pybind11/pybind11.h>

void init_GateGammaFreeFlightOptrActor(py::module &m) {

  py::class_<GateGammaFreeFlightOptrActor, G4VBiasingOperator, GateVActor>(
      m, "GateGammaFreeFlightOptrActor")
      .def(py::init<py::dict &>())
      .def("ConfigureForWorker",
           &GateGammaFreeFlightOptrActor::ConfigureForWorker)
      .def("ClearOperators", &GateGammaFreeFlightOptrActor::ClearOperators);
}
