/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateSourceManager.h"

void init_GateSourceManager(py::module &m) {

  py::class_<GateSourceManager, G4VUserPrimaryGeneratorAction,
             std::unique_ptr<GateSourceManager, py::nodelete>>(
      m, "GateSourceManager")
      .def(py::init())
      .def("AddSource", &GateSourceManager::AddSource)
      .def("Initialize", &GateSourceManager::Initialize)
      .def("SetActors", &GateSourceManager::SetActors)
      .def_readwrite("fUserEventInformationFlag",
                     &GateSourceManager::fUserEventInformationFlag)
      .def("StartMasterThread", &GateSourceManager::StartMasterThread,
           py::call_guard<py::gil_scoped_release>());
}
