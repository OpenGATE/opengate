/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4VPhysicsConstructor.hh"

/*
class PyG4VPhysicsConstructor : public G4VPhysicsConstructor {
public:
    // Inherit the constructors
    using G4VPhysicsConstructor::G4VPhysicsConstructor;

    void ConstructParticle() override {
        std::cout << "--------------> TRAMPOLINE PyG4VPhysicsConstructor::ConstructParticle " << std::endl;
        PYBIND11_OVERLOAD_PURE(void,
                               G4VPhysicsConstructor,
                               ConstructParticle,
        );
    }

    void ConstructProcess() override {
        std::cout << "--------------> TRAMPOLINE PyG4VPhysicsConstructor: :ConstructProcess " << std::endl;
        PYBIND11_OVERLOAD_PURE(void,
                               G4VPhysicsConstructor,
                               ConstructProcess,
        );
    }

};
*/
void init_G4VPhysicsConstructor(py::module &m) {


    py::class_<G4VPhysicsConstructor>(m, "G4VPhysicsConstructor");
    //.def(py::init<>());

}
