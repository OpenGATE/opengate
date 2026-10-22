/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateConfiguration.h"
#include <G4UIExecutive.hh>
#include <G4UIsession.hh>

void init_G4UIExecutive(py::module &m) {

  py::class_<G4UIExecutive>(m, "G4UIExecutive")
      .def(py::init<>([]() {
        // G4UIExecutive reads argv[0] (to find a ~/.g4session file) and gives
        // argv to QApplication, which keeps it for the whole life of the
        // application: argv must be initialised and must outlive this call,
        // hence the static storage (see #27).
        static char arg0[] = "opengate";
        static char *argv[] = {arg0, nullptr};
        return new G4UIExecutive(1, argv);
      }))
      .def("IsGUI", &G4UIExecutive::IsGUI)
      .def("SessionStart", &G4UIExecutive::SessionStart)
      .def("SetPrompt", &G4UIExecutive::SetPrompt);
}
