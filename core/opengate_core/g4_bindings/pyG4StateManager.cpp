/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

#include "G4ApplicationState.hh"
#include "G4StateManager.hh"
#include "G4ios.hh"

namespace py = pybind11;

void init_G4StateManager(py::module &m) {
  // the state manager needs this enum
  py::enum_<G4ApplicationState>(m, "G4ApplicationState")
      .value("G4State_PreInit", G4ApplicationState::G4State_PreInit)
      .value("G4State_Init", G4ApplicationState::G4State_Init)
      .value("G4State_Idle", G4ApplicationState::G4State_Idle)
      .value("G4State_GeomClosed", G4ApplicationState::G4State_GeomClosed)
      .value("G4State_EventProc", G4ApplicationState::G4State_EventProc)
      .value("G4State_Quit", G4ApplicationState::G4State_Quit)
      .value("G4State_Abort", G4ApplicationState::G4State_Abort)
      .export_values();

  py::class_<G4StateManager, std::unique_ptr<G4StateManager, py::nodelete>>(
      m, "G4StateManager")
      // No constructor need because the GetStateManager method creates the
      // singleton instance automatically get the singleton instance
      .def_static("GetStateManager", &G4StateManager::GetStateManager,
                  py::return_value_policy::reference)
      .def("GetCurrentState", &G4StateManager::GetCurrentState)
      .def("GetPreviousState", &G4StateManager::GetPreviousState)
      // Need overload_cast because SetNewState is overloaded
      // If not, pybind11 does not find the correct member function
      .def("SetNewState", py::overload_cast<const G4ApplicationState &>(
                              &G4StateManager::SetNewState))

      ;
}
