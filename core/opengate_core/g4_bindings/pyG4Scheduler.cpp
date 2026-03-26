/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Scheduler.hh"
#include "G4UserTimeStepAction.hh"

void init_G4Scheduler(py::module &m) {

  py::class_<G4Scheduler, std::unique_ptr<G4Scheduler, py::nodelete>>(
      m, "G4Scheduler")
      .def_static("Instance", &G4Scheduler::Instance,
                  py::return_value_policy::reference)
      .def("SetUserAction", &G4Scheduler::SetUserAction,
           py::arg("user_action"))
      .def("GetUserTimeStepAction", &G4Scheduler::GetUserTimeStepAction,
           py::return_value_policy::reference)
      .def("Initialize", &G4Scheduler::Initialize)
      .def("GetEndTime", &G4Scheduler::GetEndTime);
}
