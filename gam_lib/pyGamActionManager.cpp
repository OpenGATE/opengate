/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamActionManager.h"

// Main wrapper
void init_GamActionManager(py::module &m) {

    py::class_<GamActionManager,
            G4VUserActionInitialization,
            std::unique_ptr<GamActionManager, py::nodelete>>(m, "GamActionManager")
            .def(py::init())
            .def("Build", &GamActionManager::Build)
            .def("BuildForMaster", &GamActionManager::BuildForMaster)
        /*.def("start_main_thread", [](GamActionManager *sm) {
            py::gil_scoped_release release;
            sm->start_main_thread();
        })*/
            ;
}
