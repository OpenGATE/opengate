/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateKillNonInteractingParticleForLVActor.h"
#include <pybind11/pybind11.h>

void init_GateKillNonInteractingParticleForLVActor(py::module &m) {
  py::class_<
      GateKillNonInteractingParticleForLVActor,
      std::unique_ptr<GateKillNonInteractingParticleForLVActor, py::nodelete>,
      GateVActor>(m, "GateKillNonInteractingParticleForLVActor")
      .def_readwrite(
          "fListOfVolumeAncestor",
          &GateKillNonInteractingParticleForLVActor::fListOfVolumeAncestor)
      .def_property_readonly(
          "number_of_killed_particles",
          &GateKillNonInteractingParticleForLVActor::GetNumberOfKilledParticles)
      .def(
          "GetNumberOfKilledParticles",
          &GateKillNonInteractingParticleForLVActor::GetNumberOfKilledParticles)
      .def(py::init<py::dict &>());
}
