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

#include "GamVHitAttribute.h"

void init_GamVHitAttribute(py::module &m) {
    py::class_<GamVHitAttribute,
        std::unique_ptr<GamVHitAttribute, py::nodelete>>(m, "GamVHitAttribute")
        .def("FillDValue", &GamVHitAttribute::FillDValue)
        .def("FillSValue", &GamVHitAttribute::FillSValue)
        .def("FillIValue", &GamVHitAttribute::FillIValue)
        .def("Fill3Value", &GamVHitAttribute::Fill3Value);
}

