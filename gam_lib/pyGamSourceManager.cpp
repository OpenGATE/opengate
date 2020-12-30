/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamSourceManager.h"

// Main wrapper
void init_GamSourceMaster(py::module &m) {

    py::class_<GamSourceManager, G4VUserPrimaryGeneratorAction>(m, "GamSourceManager")
            .def(py::init())
            .def("add_source", &GamSourceManager::add_source)
            .def("initialize", &GamSourceManager::initialize)
            .def("start_main_thread", [](GamSourceManager *sm) {
                py::gil_scoped_release release;
                sm->start_main_thread();
            });
}
