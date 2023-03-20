/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4VModularPhysicsList.hh"
#include "G4VPhysicsConstructor.hh"
#include "G4VUserPhysicsList.hh"

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html
// Needed helper class because of the pure virtual method
class PyG4VModularPhysicsList : public G4VModularPhysicsList {
public:
  // Inherit the constructors
  using G4VModularPhysicsList::G4VModularPhysicsList;

  ~PyG4VModularPhysicsList() override {
    // std::cout << "delete PyG4VModularPhysicsList" << std::endl;
  }

  // Trampoline (need one for each virtual function)
  void SetCuts() override {
    PYBIND11_OVERLOAD(void, G4VModularPhysicsList, SetCuts, );
  }

  void ConstructParticle() override {
    PYBIND11_OVERLOAD(void, G4VModularPhysicsList, ConstructParticle, );
  }

  void ConstructProcess() override {
    PYBIND11_OVERLOAD(void, G4VModularPhysicsList, ConstructProcess, );
  }
};

// ====================================================================
// module definition
// ====================================================================
void init_G4VModularPhysicsList(py::module &m) {
  py::class_<G4VModularPhysicsList, G4VUserPhysicsList, PyG4VModularPhysicsList,
             std::unique_ptr<G4VModularPhysicsList, py::nodelete>>(
      m, "G4VModularPhysicsList", py::multiple_inheritance())
      .def(py::init<>())
      // FIXME --> cannot compile ????
      //.def("SetCuts", &G4VModularPhysicsList::SetCuts)

      /*
      .def("SetCuts", [](G4VModularPhysicsList * s) {
                        std::cout << "PY @@@@@ G4VModularPhysicsList::SetCuts"
      << std::endl; s->G4VUserPhysicsList::SetCuts();
                      })
      */

      .def("__del__",
           [](const G4VModularPhysicsList &) -> void {
             std::cerr << "---------------> deleting    G4VModularPhysicsList "
                       << std::endl;
           })

      .def("ConstructParticle", &G4VModularPhysicsList::ConstructParticle)
      .def("ConstructProcess", &G4VModularPhysicsList::ConstructProcess)
      .def("GetPhysics",
           py::overload_cast<const G4String &>(
               &G4VModularPhysicsList::GetPhysics, py::const_),
           py::return_value_policy::reference)
      .def("GetPhysics",
           py::overload_cast<G4int>(&G4VModularPhysicsList::GetPhysics,
                                    py::const_),
           py::return_value_policy::reference)
      .def("RegisterPhysics", &G4VModularPhysicsList::RegisterPhysics)
      .def("RemovePhysics",
           [](G4VModularPhysicsList *s, G4VPhysicsConstructor *p) {
             s->RemovePhysics(p);
           });
}
