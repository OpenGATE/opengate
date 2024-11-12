/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateKillInteractingParticleActor.h"

void init_GateKillInteractingParticleActor(py::module &m) {
  py::class_<GateKillInteractingParticleActor,
             std::unique_ptr<GateKillInteractingParticleActor, py::nodelete>,
             GateVActor>(m, "GateKillInteractingParticleActor")
      .def_readwrite("fListOfVolumeAncestor",
                     &GateKillInteractingParticleActor::fListOfVolumeAncestor)
      .def(py::init<py::dict &>());
}
