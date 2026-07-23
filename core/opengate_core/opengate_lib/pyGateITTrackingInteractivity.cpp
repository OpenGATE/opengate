/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateITTrackingInteractivity.h"

void init_GateITTrackingInteractivity(py::module &m) {

  py::class_<GateITTrackingInteractivity, G4ITTrackingInteractivity,
             std::unique_ptr<GateITTrackingInteractivity, py::nodelete>>(
      m, "GateITTrackingInteractivity")
      .def(py::init())
      .def("RegisterActor", &GateITTrackingInteractivity::RegisterActor,
           py::arg("actor"));
}
