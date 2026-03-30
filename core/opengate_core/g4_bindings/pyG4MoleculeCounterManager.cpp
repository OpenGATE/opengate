#include "pybind11/pybind11.h"

#include "G4MoleculeCounter.hh"
#include "G4MoleculeCounterManager.hh"
#include "G4MoleculeReactionCounter.hh"

namespace py = pybind11;

void init_G4MoleculeCounterManager(py::module &m) {
  py::class_<G4MoleculeCounterManager,
             std::unique_ptr<G4MoleculeCounterManager, py::nodelete>>(
      m, "G4MoleculeCounterManager")
      .def_static("Instance", &G4MoleculeCounterManager::Instance,
                  py::return_value_policy::reference)
      .def("SetResetCountersBeforeEvent",
           &G4MoleculeCounterManager::SetResetCountersBeforeEvent,
           py::arg("flag") = true)
      .def("SetResetCountersBeforeRun",
           &G4MoleculeCounterManager::SetResetCountersBeforeRun,
           py::arg("flag") = true)
      .def("SetResetMasterCounterWithWorkers",
           &G4MoleculeCounterManager::SetResetMasterCounterWithWorkers,
           py::arg("flag") = true)
      .def("SetAccumulateCounterIntoMaster",
           &G4MoleculeCounterManager::SetAccumulateCounterIntoMaster,
           py::arg("flag") = true)
      .def("GetResetCountersBeforeEvent",
           &G4MoleculeCounterManager::GetResetCountersBeforeEvent)
      .def("GetResetCountersBeforeRun",
           &G4MoleculeCounterManager::GetResetCountersBeforeRun)
      .def("GetResetMasterCounterWithWorkers",
           &G4MoleculeCounterManager::GetResetMasterCounterWithWorkers)
      .def("GetAccumulateCounterIntoMaster",
           &G4MoleculeCounterManager::GetAccumulateCounterIntoMaster)
      .def(
          "RegisterMoleculeCounter",
          [](G4MoleculeCounterManager *self, G4MoleculeCounter *counter) {
            return self->RegisterCounter(
                std::unique_ptr<G4VMoleculeCounter>(counter));
          },
          py::arg("counter"))
      .def(
          "RegisterReactionCounter",
          [](G4MoleculeCounterManager *self,
             G4MoleculeReactionCounter *counter) {
            return self->RegisterCounter(
                std::unique_ptr<G4VMoleculeReactionCounter>(counter));
          },
          py::arg("counter"));
}
