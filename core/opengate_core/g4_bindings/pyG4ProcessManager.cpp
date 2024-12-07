/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4ProcessManager.hh"
#include "G4StepLimiter.hh"
#include "G4VProcess.hh"

void init_G4ProcessManager(py::module &m) {

  py::class_<G4ProcessManager>(m, "G4ProcessManager")
      //.def(py::init()) # no constructor needed
      .def("AddProcess", &G4ProcessManager::AddProcess)
      .def("AddDiscreteProcess", &G4ProcessManager::AddDiscreteProcess)
      .def("GetProcess", &G4ProcessManager::GetProcess,
           py::return_value_policy::reference_internal)
      .def("GetProcessList", &G4ProcessManager::GetProcessList,
           py::return_value_policy::reference_internal);
}
