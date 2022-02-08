/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamGenericSource.h"

void init_GamGenericSource(py::module &m) {

    py::class_<GamGenericSource, GamVSource>(m, "GamGenericSource")
        .def(py::init())
        .def_readonly("fN", &GamGenericSource::fN)
        .def("InitializeUserInfo", &GamGenericSource::InitializeUserInfo)
        .def_readonly("fSkippedParticles", &GamGenericSource::fSkippedParticles);
}

