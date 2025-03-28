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
#include "GateScatterSplittingFreeFlightOptrActor.h"

void init_GateScatterSplittingFreeFlightOptrActor(py::module &m) {
  py::class_<GateScatterSplittingFreeFlightOptrActor, G4VBiasingOperator,
             GateVActor>(m, "GateScatterSplittingFreeFlightOptrActor")
      .def(py::init<py::dict &>())
      .def("ConfigureForWorker",
           &GateScatterSplittingFreeFlightOptrActor::ConfigureForWorker)
      .def("ClearOperators",
           &GateScatterSplittingFreeFlightOptrActor::ClearOperators)
      .def("GetBiasInformation",
           &GateScatterSplittingFreeFlightOptrActor::GetBiasInformation);
}
