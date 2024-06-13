/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;
#include "GateOptrLastVertexInteractionSplittingActor.h"

void init_GateOptrLastVertexInteractionSplittingActor(py::module &m) {

  py::class_<GateOptrLastVertexInteractionSplittingActor, GateVActor,
             std::unique_ptr<GateOptrLastVertexInteractionSplittingActor, py::nodelete>>(
      m, "GateOptrLastVertexInteractionSplittingActor")
      .def_readwrite(
          "fListOfVolumeAncestor",
          &GateOptrLastVertexInteractionSplittingActor::fListOfVolumeAncestor)
      .def(py::init<py::dict &>());
}
