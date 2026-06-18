/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerSpatialBlurringActor.h"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

void init_GateDigitizerSpatialBlurringActor(py::module &m) {

  py::class_<GateDigitizerSpatialBlurringActor,
             std::unique_ptr<GateDigitizerSpatialBlurringActor, py::nodelete>,
             GateVDigitizerWithOutputActor>(m,
                                            "GateDigitizerSpatialBlurringActor")
      .def(py::init<py::dict &>());
}
