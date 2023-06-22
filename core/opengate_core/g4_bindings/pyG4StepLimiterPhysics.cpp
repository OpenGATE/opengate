/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4StepLimiterPhysics.hh"

#include "G4ParticleDefinition.hh"
#include "G4ProcessManager.hh"

#include "G4BuilderType.hh"
#include "G4StepLimiter.hh"
#include "G4UserSpecialCuts.hh"

// factory
#include "G4PhysicsConstructorFactory.hh"

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void init_G4StepLimiterPhysics(py::module &m) {
  // need to specify the parent because the RegisterPhysics method of
  // G4VModularPhysicsList expects type G4VPhysicsConstructor and the python
  // binding needs to know about the inheritance
  py::class_<G4StepLimiterPhysics, G4VPhysicsConstructor,
             std::unique_ptr<G4StepLimiterPhysics, py::nodelete>>(
      m, "G4StepLimiterPhysics")
      .def(py::init());
}
