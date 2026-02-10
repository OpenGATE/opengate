/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateKillAccordingParticleNameActor.h"

void init_GateKillAccordingParticleNameActor(py::module &m) {
  py::class_<GateKillAccordingParticleNameActor,
             std::unique_ptr<GateKillAccordingParticleNameActor, py::nodelete>,
             GateVActor>(m, "GateKillAccordingParticleNameActor")
      .def(py::init<py::dict &>())
      .def_readwrite("fListOfVolumeAncestor",
                     &GateKillAccordingParticleNameActor::fListOfVolumeAncestor)
      .def("GetNumberOfKilledParticles",
           &GateKillAccordingParticleNameActor::GetNumberOfKilledParticles);
}
