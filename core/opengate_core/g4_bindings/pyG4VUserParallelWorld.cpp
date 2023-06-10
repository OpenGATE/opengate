/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

#include "G4VPhysicalVolume.hh"
#include "G4VUserParallelWorld.hh"

namespace py = pybind11;

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html
// Needed helper class because of the pure virtual method
class PyG4VUserParallelWorld : public G4VUserParallelWorld {
public:
  // Inherit the constructors
  using G4VUserParallelWorld::G4VUserParallelWorld;
  using G4VUserParallelWorld::GetWorld;

  // Trampoline (need one for each virtual function)
  void Construct() override {
    PYBIND11_OVERLOAD_PURE(void, G4VUserParallelWorld, Construct, );
  }

  // Trampoline (need one for each virtual function)
  void ConstructSD() override {
    PYBIND11_OVERLOAD_PURE(void, G4VUserParallelWorld, ConstructSD, );
  }
};

// main python wrapper
void init_G4VUserParallelWorld(py::module &m) {

  py::class_<G4VUserParallelWorld,
             std::unique_ptr<G4VUserParallelWorld, py::nodelete>,
             PyG4VUserParallelWorld>(m, "G4VUserParallelWorld")

      .def(py::init<const G4String>())
      .def("Construct", &G4VUserParallelWorld::Construct)
      .def("ConstructSD", &G4VUserParallelWorld::ConstructSD)
      .def("GetName", &G4VUserParallelWorld::GetName)
      .def("GetWorld", &PyG4VUserParallelWorld::GetWorld);
}
