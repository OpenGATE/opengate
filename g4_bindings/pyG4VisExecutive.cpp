/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamConfiguration.h"
#include <G4VisExecutive.hh>

void init_G4VisExecutive(py::module &m) {

    py::class_<G4VisExecutive>(m, "G4VisExecutive")

            .def(py::init<G4String>())
            .def("Initialise", &G4VisExecutive::Initialise)
            .def("Initialize", &G4VisExecutive::Initialize);
}
