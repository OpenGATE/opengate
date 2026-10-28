/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSourceManager.h"
#include <pybind11/pybind11.h>

void init_GateSourceManager(py::module &m) {

  py::class_<GateSourceManager, G4VUserPrimaryGeneratorAction,
             std::unique_ptr<GateSourceManager, py::nodelete>>(
      m, "GateSourceManager")
      .def(py::init())
      .def("AddSource", &GateSourceManager::AddSource)
      .def("RegisterImageBox", &GateSourceManager::RegisterImageBox)
      .def("Initialize", &GateSourceManager::Initialize)
      .def("SetActors", &GateSourceManager::SetActors)
      .def("ComputeExpectedNumberOfEvents",
           &GateSourceManager::ComputeExpectedNumberOfEvents)
      .def("GetExpectedNumberOfEvents",
           &GateSourceManager::GetExpectedNumberOfEvents)
      .def("GetRunGeneratedEvents", &GateSourceManager::GetRunGeneratedEvents)
      .def("GetTotalGeneratedEvents",
           &GateSourceManager::GetTotalGeneratedEvents)
      .def("GetCurrentSimulationTime",
           &GateSourceManager::GetCurrentSimulationTime)
      .def("GetCurrentRunId", &GateSourceManager::GetCurrentRunId)
      .def_static("GetPlatformMaxPrimariesPerRun",
                  &GateSourceManager::GetPlatformMaxPrimariesPerRun)
      .def_readwrite("fUserEventInformationFlag",
                     &GateSourceManager::fUserEventInformationFlag)
      .def("SetProgressReportCallback",
           &GateSourceManager::SetProgressReportCallback)
      .def("StartMasterThread", &GateSourceManager::StartMasterThread,
           py::call_guard<py::gil_scoped_release>());
}
