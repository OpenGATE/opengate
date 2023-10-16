#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4PhysicsFreeVector.hh"

void init_G4PhysicsFreeVector(py::module &m) {

  py::class_<G4PhysicsFreeVector>(m, "G4PhysicsFreeVector")

      .def(py::init())

      .def("InsertValues", &G4PhysicsFreeVector::InsertValues,
           py::return_value_policy::automatic);

  // Create an alias
  m.attr("G4MaterialPropertyVector") = m.attr("G4PhysicsFreeVector");
}
