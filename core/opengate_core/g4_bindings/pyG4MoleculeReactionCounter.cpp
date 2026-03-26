#include "pybind11/pybind11.h"

#include "G4MoleculeReactionCounter.hh"

namespace py = pybind11;

void init_G4MoleculeReactionCounter(py::module &m)
{
  py::class_<G4MoleculeReactionCounter,
             std::unique_ptr<G4MoleculeReactionCounter, py::nodelete>>(
      m, "G4MoleculeReactionCounter")
      .def(py::init<>())
      .def(py::init<G4String>())
      .def("Initialize", &G4MoleculeReactionCounter::Initialize)
      .def("GetName", &G4MoleculeReactionCounter::GetName)
      .def("SetVerbose", &G4MoleculeReactionCounter::SetVerbose)
      .def("SetTimeComparer", &G4MoleculeReactionCounter::SetTimeComparer)
      .def("SetCheckTimeConsistencyWithScheduler",
           &G4MoleculeReactionCounter::SetCheckTimeConsistencyWithScheduler)
      .def("SetCheckRecordedTimeConsistency",
           &G4MoleculeReactionCounter::SetCheckRecordedTimeConsistency)
      .def("SetActiveLowerBound", &G4MoleculeReactionCounter::SetActiveLowerBound,
           py::arg("time"), py::arg("inclusive") = true)
      .def("SetActiveUpperBound", &G4MoleculeReactionCounter::SetActiveUpperBound,
           py::arg("time"), py::arg("inclusive") = true)
      .def("GetManagedId", &G4MoleculeReactionCounter::GetManagedId);
}
