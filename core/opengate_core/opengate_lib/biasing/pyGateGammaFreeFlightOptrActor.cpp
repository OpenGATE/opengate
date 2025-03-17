/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;
#include "G4VBiasingOperator.hh"
#include "GateGammaFreeFlightOptrActor.h"

void init_GateGammaFreeFlightOptrActor(py::module &m) {

  py::class_<GateGammaFreeFlightOptrActor, G4VBiasingOperator, GateVActor,
             std::unique_ptr<GateGammaFreeFlightOptrActor, py::nodelete>>(
      m, "GateGammaFreeFlightOptrActor")
      .def(py::init<py::dict &>())
      .def("ConfigureForWorker",
           &GateGammaFreeFlightOptrActor::ConfigureForWorker);
}
