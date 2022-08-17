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

#include "GateUniqueVolumeIDManager.h"

void init_GateUniqueVolumeIDManager(py::module &m) {
    py::class_<GateUniqueVolumeIDManager,
        std::unique_ptr<GateUniqueVolumeIDManager, py::nodelete>>(m, "GateUniqueVolumeIDManager")
        .def("GetInstance", &GateUniqueVolumeIDManager::GetInstance)
        .def("GetAllVolumeIDs", &GateUniqueVolumeIDManager::GetAllVolumeIDs);
}

