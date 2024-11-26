/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateKillAccordingProcessesActor.h"

void init_GateKillAccordingProcessesActor(py::module &m) {
  py::class_<GateKillAccordingProcessesActor,
             std::unique_ptr<GateKillAccordingProcessesActor, py::nodelete>,
             GateVActor>(m, "GateKillAccordingProcessesActor")
      .def_readwrite("fListOfVolumeAncestor",
                     &GateKillAccordingProcessesActor::fListOfVolumeAncestor)
      .def(py::init<py::dict &>());
}
