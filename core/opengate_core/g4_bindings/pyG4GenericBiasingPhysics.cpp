/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/stl_bind.h>

namespace py = pybind11;

#include "G4GenericBiasingPhysics.hh"
#include "G4PhysListFactory.hh"
#include "G4VModularPhysicsList.hh"
#include <G4VPhysicsConstructor.hh>

void init_G4GenericBiasingPhysics(py::module &m) {

  /*py::class_<G4GenericBiasingPhysics,G4VPhysicsConstructor>(m,
     "G4GenericBiasingPhysics") .def("PhysicsBias",
     &G4GenericBiasingPhysics::PhysicsBias,
     py::return_value_policy::reference);*/

  py::class_<G4GenericBiasingPhysics, G4VPhysicsConstructor>(
      m, "G4GenericBiasingPhysics")
      .def("PhysicsBias",
           py::overload_cast<const G4String &, const std::vector<G4String> &>(
               &G4GenericBiasingPhysics::PhysicsBias));
}
