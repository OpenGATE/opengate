/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamConfiguration.h"
#include "G4UIExecutive.hh"
#include "G4VisExecutive.hh"
//#include "qglobal.h"
//#include <G4UIQt.hh>
//#include <qmainwindow.h>


void init_G4UIQt(py::module & /*m*/) {
    /*  py::class_<G4UIQt>(m, "G4UIQt")

          .def("GetMainWindow", &G4UIQt::GetMainWindow)
          .def("AddButton", &G4UIQt::AddButton)
          .def("AddIcon", &G4UIQt::AddIcon)
          .def("AddMenu", &G4UIQt::AddMenu)
          .def("PauseSessionStart", &G4UIQt::PauseSessionStart)
          .def("SessionTerminate", &G4UIQt::SessionTerminate);
  */
}
