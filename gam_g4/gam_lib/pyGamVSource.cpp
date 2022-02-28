/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamVSource.h"

void init_GamVSource(py::module &m) {

    py::class_<GamVSource,
        std::unique_ptr<GamVSource, py::nodelete>>(m, "GamVSource")
        .def(py::init())
            //.def_readonly("events_per_run", &GamVSource::fEventsPerRun)
        .def("InitializeUserInfo", &GamVSource::InitializeUserInfo);
}


