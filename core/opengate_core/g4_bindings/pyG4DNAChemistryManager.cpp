#include "pybind11/pybind11.h"
#include "G4DNAChemistryManager.hh"
#include "G4Scheduler.hh"
#include "G4VUserChemistryList.hh"

namespace py = pybind11;

void init_G4DNAChemistryManager(py::module &m)
{
  py::class_<G4DNAChemistryManager>(m, "G4DNAChemistryManager")
      .def_static(
          "Instance",
          &G4DNAChemistryManager::Instance,
          py::return_value_policy::reference)

      .def(
          "Initialize",
          [](G4DNAChemistryManager *self,
             py::object pychemlist) {
            // The Python-side object must hold a capsule containing
            // a raw pointer to a G4VUserChemistryList.
            // This mirrors what other GATE-10 pybind wrappers do
            // for user-defined C++ classes.
            if (!pychemlist) {
              throw std::runtime_error(
                  "Initialize() requires a ChemistryList object");
            }

            // Retrieve pointer from capsule
            auto ptr = pychemlist.attr("__cpp__").cast<G4VUserChemistryList *>();
            if (!ptr) {
              throw std::runtime_error(
                  "Invalid ChemistryList: missing or null __cpp__ pointer");
            }

            self->Initialize(ptr);
          },
          py::arg("chemistry_list"),
          "Initialize the DNA chemistry system with a user-defined ChemistryList")

      .def(
          "SetChemistryActive",
          &G4DNAChemistryManager::SetChemistryActive,
          py::arg("chemistry_active_flag"),
          "Enable or disable Geant4-DNA chemistry")

      .def_static(
          "IsActivated",
          &G4DNAChemistryManager::IsActivated,
          "Return True if DNA chemistry is active")

      .def(
          "GetChemistryStartTime",
          &G4DNAChemistryManager::GetChemistryStartTime,
          "Return the chemistry start time")

      .def(
          "SetChemistryStartTime",
          &G4DNAChemistryManager::SetChemistryStartTime,
          py::arg("chemistry_start_time"),
          "Set the chemistry start time")

      .def(
          "Run",
          [](G4DNAChemistryManager *self) {
            // Convenience wrapper, mirrors C++ API
            self->Run();
          },
          "Run the chemistry stage using the underlying G4Scheduler")

      // expose the underlying scheduler (read-only)
      .def_property_readonly(
          "scheduler",
          [](G4DNAChemistryManager *self) {
            return G4Scheduler::Instance();
          },
          py::return_value_policy::reference,
          "Return the underlying G4Scheduler instance");
}