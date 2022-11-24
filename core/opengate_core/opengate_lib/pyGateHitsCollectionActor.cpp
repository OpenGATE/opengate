/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "digitizer/GateDigitizerHitsCollectionActor.h"

void init_GateHitsCollectionActor(py::module &m) {

  py::class_<GateDigitizerHitsCollectionActor,
             std::unique_ptr<GateDigitizerHitsCollectionActor, py::nodelete>,
             GateVActor>(m, "GateDigitizerHitsCollectionActor")
      .def(py::init<py::dict &>());
}
