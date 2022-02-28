/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamVoxelsSource.h"

void init_GamVoxelsSource(py::module &m) {

    py::class_<GamVoxelsSource, GamGenericSource>(m, "GamVoxelsSource")
        .def(py::init())
        .def("GetSPSVoxelPosDistribution", &GamVoxelsSource::GetSPSVoxelPosDistribution,
             py::return_value_policy::reference_internal)
        .def("InitializeUserInfo", &GamVoxelsSource::InitializeUserInfo);
}

