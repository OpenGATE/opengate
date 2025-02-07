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
#include "GateComptonSplittingFreeFlightOptrActor.h"

void init_GateComptonSplittingFreeFlightOptrActor(py::module &m) {
  py::class_<
      GateComptonSplittingFreeFlightOptrActor, G4VBiasingOperator, GateVActor,
      std::unique_ptr<GateComptonSplittingFreeFlightOptrActor, py::nodelete>>(
      m, "GateComptonSplittingFreeFlightOptrActor")
      .def(py::init<py::dict &>())
      .def("ConfigureForWorker",
           &GateComptonSplittingFreeFlightOptrActor::ConfigureForWorker)
      .def("GetSplitStats",
           &GateComptonSplittingFreeFlightOptrActor::GetSplitStats);
}
