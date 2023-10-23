/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateKillActor.h"

void init_GateKillActor(py::module &m) {
  py::class_<GateKillActor, std::unique_ptr<GateKillActor, py::nodelete>,
             GateVActor>(m, "GateKillActor")
      .def(py::init<py::dict &>())
      .def_readonly("fNbOfKilledParticles",
                    &GateKillActor::fNbOfKilledParticles);
}
