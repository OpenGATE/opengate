/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateMaterialMuHandler.h"

void init_GateMaterialMuHandler(py::module &m) {
  py::class_<GateMaterialMuHandler,
             std::unique_ptr<GateMaterialMuHandler, py::nodelete>>(
      m, "GateMaterialMuHandler")
      .def("GetInstance", &GateMaterialMuHandler::GetInstance)
      .def("GetMu", &GateMaterialMuHandler::GetMu);
}
