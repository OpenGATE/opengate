/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;
#include "GateLastVertexInteractionSplittingActor.h"

void init_GateLastVertexInteractionSplittingActor(py::module &m) {

  py::class_<
      GateLastVertexInteractionSplittingActor, GateVActor,
      std::unique_ptr<GateLastVertexInteractionSplittingActor, py::nodelete>>(
      m, "GateLastVertexInteractionSplittingActor")
      .def_readwrite(
          "fListOfVolumeAncestor",
          &GateLastVertexInteractionSplittingActor::fListOfVolumeAncestor)
      .def(py::init<py::dict &>())
      .def("GetNumberOfKilledParticles",
           &GateLastVertexInteractionSplittingActor::GetNumberOfKilledParticles)
      .def("GetNumberOfReplayedParticles",
           &GateLastVertexInteractionSplittingActor::GetNumberOfReplayedParticles);
}

