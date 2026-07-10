/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigiAttributeLastProcessDefinedStepInVolumeActor.h"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

void init_GateDigiAttributeLastProcessDefinedStepInVolumeActor(py::module &m) {

  py::class_<
      GateDigiAttributeLastProcessDefinedStepInVolumeActor,
      std::unique_ptr<GateDigiAttributeLastProcessDefinedStepInVolumeActor,
                      py::nodelete>,
      GateVActor>(m, "GateDigiAttributeLastProcessDefinedStepInVolumeActor")
      .def(py::init<py::dict &>());
}
