/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamConfiguration.h"
#include <G4UIExecutive.hh>
#include <G4UIsession.hh>

void init_G4UIExecutive(py::module &m) {

    py::class_<G4UIExecutive>(m, "G4UIExecutive")
        .def(py::init<>([]() {
                            G4int argc = 1;
                            char *argv[1];
                            return new G4UIExecutive(argc, argv);
                        }
        ))
        .def("IsGUI", &G4UIExecutive::IsGUI)
        .def("SessionStart", &G4UIExecutive::SessionStart)
        .def("SetPrompt", &G4UIExecutive::SetPrompt);

}
