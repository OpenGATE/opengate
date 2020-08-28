
#include <pybind11/pybind11.h>
//#include <pybind11/operators.h>

namespace py = pybind11;

#include "G4VModularPhysicsList.hh"
#include "G4VUserPhysicsList.hh"

// ====================================================================
// thin wrappers
// ====================================================================
// namespace pyG4VModularPhysicsList {

// struct CB_G4VModularPhysicsList :
//   G4VModularPhysicsList, wrapper<G4VModularPhysicsList> {

//   void SetCuts() {
//     get_override("SetCuts")();
//   }

// };

// // GetPhysics()
// const G4VPhysicsConstructor*
//       (G4VModularPhysicsList::*f1_GetPhysics)(G4int) const
//   = &G4VModularPhysicsList::GetPhysics;
// const G4VPhysicsConstructor*
//       (G4VModularPhysicsList::*f2_GetPhysics)(const G4String&) const
//   = &G4VModularPhysicsList::GetPhysics;

// }

// using namespace pyG4VModularPhysicsList;

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html
// Needed helper class because of the pure virtual method
class PyG4VModularPhysicsList : public G4VModularPhysicsList {
public:
    /* Inherit the constructors */
    using G4VModularPhysicsList::G4VModularPhysicsList;

    /* Trampoline (need one for each virtual function) */

    void SetCuts() override {
        std::cout << "--------------> TRAMPOLINE PyG4VModularPhysicsList::SetCuts " << std::endl;
        PYBIND11_OVERLOAD(void,
                          G4VModularPhysicsList,
                          SetCuts,
        );
    }

    void ConstructParticle() override {
        std::cout << "--------------> TRAMPOLINE PyG4VModularPhysicsList::ConstructParticle " << std::endl;
        PYBIND11_OVERLOAD(void,
                          G4VModularPhysicsList,
                          ConstructParticle,
        );
    }

    void ConstructProcess() override {
        std::cout << "--------------> TRAMPOLINE PyG4VModularPhysicsList::ConstructProcess " << std::endl;
        PYBIND11_OVERLOAD(void,
                          G4VModularPhysicsList,
                          ConstructProcess,
        );
    }

};

// ====================================================================
// module definition
// ====================================================================
void init_G4VModularPhysicsList(py::module &m) {
    py::class_<G4VModularPhysicsList, G4VUserPhysicsList, PyG4VModularPhysicsList>(m, "G4VModularPhysicsList",
                                                                                   py::multiple_inheritance())

        .def(py::init<>())

            // FIXME --> cannot compile ????
            //.def("SetCuts", &G4VModularPhysicsList::SetCuts)

            /*
            .def("SetCuts", [](G4VModularPhysicsList * s) {
                              std::cout << "PY @@@@@ G4VModularPhysicsList::SetCuts" << std::endl;
                              s->G4VUserPhysicsList::SetCuts();
                            })
            */


            // virtual (needed)
        .def("ConstructParticle", &G4VModularPhysicsList::ConstructParticle)
        .def("ConstructProcess", &G4VModularPhysicsList::ConstructProcess)


        .def("RegisterPhysics", &G4VModularPhysicsList::RegisterPhysics)
        // .def("GetPhysics",       f1_GetPhysics,
        //      return_value_policy<reference_existing_object>())
        // .def("GetPhysics",       f2_GetPhysics,
        //      return_value_policy<reference_existing_object>())
        ;
}

