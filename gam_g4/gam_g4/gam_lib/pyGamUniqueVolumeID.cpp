/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

namespace py = pybind11;

#include "GamUniqueVolumeID.h"

void init_GamUniqueVolumeID(py::module &m) {
    // need to nodelete to avoid double destruction in c++ and py sides.
    py::class_<GamUniqueVolumeID,
        std::unique_ptr<GamUniqueVolumeID, py::nodelete>>(m, "GamUniqueVolumeID")
        .def("GetVolumeDepthID", &GamUniqueVolumeID::GetVolumeDepthID)
        .def_readonly("fID", &GamUniqueVolumeID::fID);
}

