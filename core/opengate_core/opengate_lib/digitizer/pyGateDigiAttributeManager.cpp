/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4Step.hh"
#include "GateDigiAttributeManager.h"
#include "GateVDigiAttribute.h"

void init_GateDigiAttributeManager(py::module &m) {

  py::class_<GateDigiAttributeManager,
             std::unique_ptr<GateDigiAttributeManager, py::nodelete>>(
      m, "GateDigiAttributeManager")
      .def("DefineDigiAttribute",
           &GateDigiAttributeManager::DefineDigiAttribute)
      .def("GetInstance", &GateDigiAttributeManager::GetInstance)
      .def("DumpAvailableDigiAttributeNames",
           &GateDigiAttributeManager::DumpAvailableDigiAttributeNames)
      .def("GetDigiAttributeByName",
           &GateDigiAttributeManager::GetDigiAttributeByName)
      .def("GetAvailableDigiAttributeNames",
           &GateDigiAttributeManager::GetAvailableDigiAttributeNames);
}
