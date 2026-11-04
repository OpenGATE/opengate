/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateKillAccordingParticleNameLVActor.h"
#include <pybind11/pybind11.h>

void init_GateKillAccordingParticleNameLVActor(py::module &m) {
  py::class_<GateKillAccordingParticleNameLVActor,
             std::unique_ptr<GateKillAccordingParticleNameLVActor, py::nodelete>,
             GateVActor>(m, "GateKillAccordingParticleNameLVActor")
      .def(py::init<py::dict &>())
      .def_readwrite("fListOfVolumeAncestor",
                     &GateKillAccordingParticleNameLVActor::fListOfVolumeAncestor)
      .def("GetNumberOfKilledParticles",
           &GateKillAccordingParticleNameLVActor::GetNumberOfKilledParticles);
}
