/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateKillNonInteractingParticleActor.h"

void init_GateKillNonInteractingParticleActor(py::module &m) {
  py::class_<GateKillNonInteractingParticleActor,
             std::unique_ptr<GateKillNonInteractingParticleActor, py::nodelete>,
             GateVActor>(m, "GateKillNonInteractingParticleActor")
      .def_readwrite(
          "fListOfVolumeAncestor",
          &GateKillNonInteractingParticleActor::fListOfVolumeAncestor)
      .def(py::init<py::dict &>());
}
