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

#include "GamHitAttributeManager.h"
#include "GamVHitAttribute.h"
#include "G4Step.hh"

void init_GamHitAttributeManager(py::module &m) {

    py::class_<GamHitAttributeManager,
        std::unique_ptr<GamHitAttributeManager, py::nodelete>>(m, "GamHitAttributeManager")
        .def("DefineHitAttribute", &GamHitAttributeManager::DefineHitAttribute)
        .def("GetInstance", &GamHitAttributeManager::GetInstance);
}
