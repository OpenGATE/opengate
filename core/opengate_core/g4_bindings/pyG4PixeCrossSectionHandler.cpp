/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4PixeCrossSectionHandler.hh"

void init_G4PixeCrossSectionHandler(py::module &m) {
  py::class_<G4PixeCrossSectionHandler>(m, "G4PixeCrossSectionHandler")

      .def(py::init<>())
      .def("PrintData", &G4PixeCrossSectionHandler::PrintData);
}
