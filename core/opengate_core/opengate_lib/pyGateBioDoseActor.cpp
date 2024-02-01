/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "GateBioDoseActor.h"

namespace py = pybind11;

void init_GateBioDoseActor(py::module &m) {
  py::class_<GateBioDoseActor, std::unique_ptr<GateBioDoseActor, py::nodelete>,
             GateVActor>(m, "GateBioDoseActor")
      .def(py::init<py::dict &>())
      .def_readwrite("NbOfEvent", &GateBioDoseActor::fNbOfEvent)
			;
}
