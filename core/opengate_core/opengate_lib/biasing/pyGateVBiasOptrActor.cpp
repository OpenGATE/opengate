/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;
#include "G4VBiasingOperator.hh"
#include "GateVBiasOptrActor.h"

void init_GateVBiasOptrActor(py::module &m) {

  py::class_<GateVBiasOptrActor, GateVActor>(m, "GateVBiasOptrActor")
      .def("ConfigureForWorker", &GateVBiasOptrActor::ConfigureForWorker)
      .def("ClearOperators", &GateVBiasOptrActor::ClearOperators);
}
