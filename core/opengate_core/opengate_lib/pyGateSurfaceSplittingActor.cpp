/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateSurfaceSplittingActor.h"

void init_GateSurfaceSplittingActor(py::module &m) {
  py::class_<GateSurfaceSplittingActor, std::unique_ptr<GateSurfaceSplittingActor, py::nodelete>,GateVActor>(m, "GateSurfaceSplittingActor")
      .def(py::init<py::dict &>())
  .def_readwrite("fListOfVolumeAncestor",&GateSurfaceSplittingActor::fListOfVolumeAncestor)
      .def(py::init<py::dict &>());
}
