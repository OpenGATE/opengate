/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;
#include "GateLastVertexInteractionSplittingActorOld.h"

void init_GateLastVertexInteractionSplittingActorOld(py::module &m) {

  py::class_<GateLastVertexInteractionSplittingActorOld, GateVActor,
             std::unique_ptr<GateLastVertexInteractionSplittingActorOld, py::nodelete>>(
      m, "GateLastVertexInteractionSplittingActorOld")
      .def_readwrite(
          "fListOfVolumeAncestor",
          &GateLastVertexInteractionSplittingActorOld::fListOfVolumeAncestor)
      .def(py::init<py::dict &>());
}
