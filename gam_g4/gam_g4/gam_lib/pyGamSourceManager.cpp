/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamSourceManager.h"

void init_GamSourceManager(py::module &m) {

    py::class_<GamSourceManager, G4VUserPrimaryGeneratorAction,
            std::unique_ptr<GamSourceManager, py::nodelete>>(m, "GamSourceManager")
            .def(py::init())
            .def("AddSource", &GamSourceManager::AddSource)
            .def("Initialize", &GamSourceManager::Initialize)
            .def("StartMasterThread", [](GamSourceManager *sm) {
                py::gil_scoped_release release;
                sm->StartMasterThread();
            });
}
