#include "pybind11/pybind11.h"

#include "G4MoleculeCounterTimeComparer.hh"

namespace py = pybind11;

void init_G4MoleculeCounterTimeComparer(py::module &m)
{
  py::class_<G4MoleculeCounterTimeComparer>(m, "G4MoleculeCounterTimeComparer")
      .def(py::init<>())
      .def("SetFixedPrecision", &G4MoleculeCounterTimeComparer::SetFixedPrecision)
      .def_static(
          "CreateWithFixedPrecision",
          &G4MoleculeCounterTimeComparer::CreateWithFixedPrecision)
      .def_static(
          "CreateWithVariablePrecision",
          py::overload_cast<const std::map<G4double, G4double> &>(
              &G4MoleculeCounterTimeComparer::CreateWithVariablePrecision))
      .def("GetPrecisionAtTime",
           &G4MoleculeCounterTimeComparer::GetPrecisionAtTime);
}
