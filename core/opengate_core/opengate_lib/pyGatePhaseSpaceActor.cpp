/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GatePhaseSpaceActor.h"
#include <pybind11/pybind11.h>

void init_GatePhaseSpaceActor(py::module &m) {

  py::class_<GatePhaseSpaceActor, GateVActor>(m, "GatePhaseSpaceActor")
      .def(py::init<py::dict &>())
      .def("GetNumberOfAbsorbedEvents",
           &GatePhaseSpaceActor::GetNumberOfAbsorbedEvents)
      .def("GetTotalNumberOfEntries",
           &GatePhaseSpaceActor::GetTotalNumberOfEntries);
}
