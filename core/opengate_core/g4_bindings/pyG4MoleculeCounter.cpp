#include "pybind11/pybind11.h"
#include "pybind11/stl.h"

#include "G4MoleculeCounter.hh"
#include "G4MoleculeTable.hh"

namespace py = pybind11;

void init_G4MoleculeCounter(py::module &m) {
  py::class_<G4MoleculeCounter,
             std::unique_ptr<G4MoleculeCounter, py::nodelete>>(
      m, "G4MoleculeCounter")
      .def(py::init<>())
      .def(py::init<G4String>())
      .def("Initialize", &G4MoleculeCounter::Initialize)
      .def("GetName", &G4MoleculeCounter::GetName)
      .def("SetVerbose", &G4MoleculeCounter::SetVerbose)
      .def("SetTimeComparer", &G4MoleculeCounter::SetTimeComparer)
      .def(
          "IgnoreMolecule",
          [](G4MoleculeCounter *self, const std::string &name) {
            auto *molecule =
                G4MoleculeTable::Instance()->GetMoleculeDefinition(name, false);
            if (molecule == nullptr) {
              throw std::runtime_error("Unknown molecule name: " + name);
            }
            self->IgnoreMolecule(molecule);
          },
          py::arg("name"))
      .def("RegisterAll", &G4MoleculeCounter::RegisterAll)
      .def("SetCheckTimeConsistencyWithScheduler",
           &G4MoleculeCounter::SetCheckTimeConsistencyWithScheduler)
      .def("SetCheckRecordedTimeConsistency",
           &G4MoleculeCounter::SetCheckRecordedTimeConsistency)
      .def("SetActiveLowerBound", &G4MoleculeCounter::SetActiveLowerBound,
           py::arg("time"), py::arg("inclusive") = true)
      .def("SetActiveUpperBound", &G4MoleculeCounter::SetActiveUpperBound,
           py::arg("time"), py::arg("inclusive") = true)
      .def("GetManagedId", &G4MoleculeCounter::GetManagedId);
}
