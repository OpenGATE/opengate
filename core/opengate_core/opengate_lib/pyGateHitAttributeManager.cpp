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

#include "GateHitAttributeManager.h"
#include "GateVHitAttribute.h"
#include "G4Step.hh"

void init_GateHitAttributeManager(py::module &m) {

    py::class_<GateHitAttributeManager,
        std::unique_ptr<GateHitAttributeManager, py::nodelete>>(m, "GateHitAttributeManager")
        .def("DefineHitAttribute", &GateHitAttributeManager::DefineHitAttribute)
        .def("GetInstance", &GateHitAttributeManager::GetInstance)
        .def("DumpAvailableHitAttributeNames", &GateHitAttributeManager::DumpAvailableHitAttributeNames)
        .def("GetAvailableHitAttributeNames", &GateHitAttributeManager::GetAvailableHitAttributeNames);
}
