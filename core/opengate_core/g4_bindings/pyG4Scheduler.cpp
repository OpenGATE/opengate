/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4ITTrackingInteractivity.hh"
#include "G4Scheduler.hh"
#include "G4UserTimeStepAction.hh"

void init_G4Scheduler(py::module &m) {

  py::class_<G4Scheduler, std::unique_ptr<G4Scheduler, py::nodelete>>(
      m, "G4Scheduler")
      .def_static("Instance", &G4Scheduler::Instance,
                  py::return_value_policy::reference)
      .def(
          "SetUserAction",
          [](G4Scheduler &self, py::object user_action) {
            if (user_action.is_none()) {
              self.SetUserAction(static_cast<G4UserTimeStepAction *>(nullptr));
            } else {
              self.SetUserAction(user_action.cast<G4UserTimeStepAction *>());
            }
          },
          py::arg("user_action"))
      .def(
          "SetInteractivity",
          [](G4Scheduler &self, py::object interactivity) {
            if (interactivity.is_none()) {
              self.SetInteractivity(
                  static_cast<G4ITTrackingInteractivity *>(nullptr));
            } else {
              self.SetInteractivity(
                  interactivity.cast<G4ITTrackingInteractivity *>());
            }
          },
          py::arg("interactivity"))
      .def("GetUserTimeStepAction", &G4Scheduler::GetUserTimeStepAction,
           py::return_value_policy::reference)
      .def("Initialize", &G4Scheduler::Initialize)
      .def("GetEndTime", &G4Scheduler::GetEndTime);
}
