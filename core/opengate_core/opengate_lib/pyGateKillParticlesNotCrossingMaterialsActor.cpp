/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateKillParticlesNotCrossingMaterialsActor.h"

void init_GateKillParticlesNotCrossingMaterialsActor(py::module &m) {
  py::class_<
      GateKillParticlesNotCrossingMaterialsActor,
      std::unique_ptr<GateKillParticlesNotCrossingMaterialsActor, py::nodelete>,
      GateVActor>(m, "GateKillParticlesNotCrossingMaterialsActor")
      .def_readwrite(
          "fListOfVolumeAncestor",
          &GateKillParticlesNotCrossingMaterialsActor::fListOfVolumeAncestor)
      .def(py::init<py::dict &>());
}
