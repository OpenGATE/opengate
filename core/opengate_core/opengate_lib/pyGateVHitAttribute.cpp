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

#include "GateVHitAttribute.h"

void init_GateVHitAttribute(py::module &m) {
    py::class_<GateVHitAttribute,
        std::unique_ptr<GateVHitAttribute, py::nodelete>>(m, "GateVHitAttribute")
        .def("FillDValue", &GateVHitAttribute::FillDValue)
        .def("FillSValue", &GateVHitAttribute::FillSValue)
        .def("FillIValue", &GateVHitAttribute::FillIValue)
        .def("Fill3Value", &GateVHitAttribute::Fill3Value);
}

