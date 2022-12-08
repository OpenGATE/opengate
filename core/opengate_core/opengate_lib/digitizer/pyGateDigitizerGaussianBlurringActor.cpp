/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateDigitizerGaussianBlurringActor.h"

void init_GateHitsGaussianBlurringActor(py::module &m) {

  py::class_<GateDigitizerGaussianBlurringActor,
             std::unique_ptr<GateDigitizerGaussianBlurringActor, py::nodelete>,
             GateVActor>(m, "GateDigitizerGaussianBlurringActor")
      .def(py::init<py::dict &>());
}
