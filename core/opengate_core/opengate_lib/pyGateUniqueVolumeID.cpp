/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateUniqueVolumeID.h"

void init_GateUniqueVolumeID(py::module &m) {
  // need to nodelete to avoid double destruction in c++ and py sides.
  py::class_<GateUniqueVolumeID,
             std::unique_ptr<GateUniqueVolumeID, py::nodelete>>(
      m, "GateUniqueVolumeID")
      .def("GetDepth", &GateUniqueVolumeID::GetDepth)
      .def_readonly("fID", &GateUniqueVolumeID::fID)
      .def_readonly("fNumericID", &GateUniqueVolumeID::fNumericID);
}
