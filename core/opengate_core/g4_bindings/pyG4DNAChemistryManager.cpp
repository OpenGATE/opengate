#include "G4DNAChemistryManager.hh"
#include "G4Scheduler.hh"
#include "G4VUserChemistryList.hh"
#include "pybind11/pybind11.h"

namespace py = pybind11;

void init_G4DNAChemistryManager(py::module &m) {
  py::class_<G4DNAChemistryManager,
             std::unique_ptr<G4DNAChemistryManager, py::nodelete>>(
      m, "G4DNAChemistryManager")
      .def_static("Instance", &G4DNAChemistryManager::Instance,
                  py::return_value_policy::reference)

      .def(
          "SetChemistryList",
          [](G4DNAChemistryManager *self, py::object pychemlist) {
            if (!pychemlist) {
              throw std::runtime_error(
                  "SetChemistryList() requires a ChemistryList object");
            }
            auto ptr = pychemlist.cast<G4VUserChemistryList *>();
            if (!ptr) {
              throw std::runtime_error("Invalid ChemistryList: null pointer");
            }
            self->SetChemistryList(*ptr);
          },
          py::arg("chemistry_list"),
          "Register a user-defined ChemistryList with the DNA chemistry "
          "manager")

      .def("Initialize",
           py::overload_cast<>(&G4DNAChemistryManager::Initialize),
           py::call_guard<py::gil_scoped_release>(),
           "Initialize the DNA chemistry system")

      .def("SetChemistryActivation",
           &G4DNAChemistryManager::SetChemistryActivation,
           py::arg("chemistry_active_flag"),
           "Enable or disable Geant4-DNA chemistry")

      .def_static("IsActivated", &G4DNAChemistryManager::IsActivated,
                  "Return True if DNA chemistry is active")

      .def("Run", &G4DNAChemistryManager::Run,
           py::call_guard<py::gil_scoped_release>(),
           "Run the chemistry stage using the underlying G4Scheduler")

      // expose the underlying scheduler (read-only)
      .def_property_readonly(
          "scheduler",
          [](G4DNAChemistryManager *self) { return G4Scheduler::Instance(); },
          py::return_value_policy::reference,
          "Return the underlying G4Scheduler instance");
}
