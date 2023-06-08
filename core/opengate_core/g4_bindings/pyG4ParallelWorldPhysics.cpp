/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4ParallelWorldPhysics.hh"
#include "G4VPhysicsConstructor.hh"

void init_G4ParallelWorldPhysics(py::module &m) {
  py::class_<G4ParallelWorldPhysics, G4VPhysicsConstructor,
             std::unique_ptr<G4ParallelWorldPhysics, py::nodelete>>(
      m, "G4ParallelWorldPhysics")
      .def(py::init<const G4String, G4bool>());
}
