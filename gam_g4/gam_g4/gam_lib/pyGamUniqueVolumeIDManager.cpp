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

#include "GamUniqueVolumeIDManager.h"

void init_GamUniqueVolumeIDManager(py::module &m) {
    py::class_<GamUniqueVolumeIDManager,
            std::unique_ptr<GamUniqueVolumeIDManager, py::nodelete>>(m, "GamUniqueVolumeIDManager")
            .def("GetAllVolumeIDs", &GamUniqueVolumeIDManager::GetAllVolumeIDs);
}

