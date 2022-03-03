/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamConfiguration.h"
#include <G4VisManager.hh>

void init_G4VisManager(py::module &m) {

    py::class_<G4VisManager>(m, "G4VisManager")

        .def("Initialise", &G4VisManager::Initialise)
        .def("Initialize", &G4VisManager::Initialize);

}
