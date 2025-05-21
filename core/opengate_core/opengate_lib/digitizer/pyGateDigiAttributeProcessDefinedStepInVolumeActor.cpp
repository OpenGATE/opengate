/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateDigiAttributeProcessDefinedStepInVolumeActor.h"

void init_GateDigiAttributeProcessDefinedStepInVolumeActor(py::module &m) {

  py::class_<GateDigiAttributeProcessDefinedStepInVolumeActor,
             std::unique_ptr<GateDigiAttributeProcessDefinedStepInVolumeActor,
                             py::nodelete>,
             GateVActor>(m, "GateDigiAttributeProcessDefinedStepInVolumeActor")
      .def(py::init<py::dict &>());
}
