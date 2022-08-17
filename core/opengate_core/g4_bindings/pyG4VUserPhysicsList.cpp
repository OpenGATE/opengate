/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4VUserPhysicsList.hh"

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html
// Needed helper class because of the pure virtual method
class PyG4VUserPhysicsList : public G4VUserPhysicsList {
public:
    // Inherit the constructors
    using G4VUserPhysicsList::G4VUserPhysicsList;

    // Trampoline (need one for each virtual function)
    void ConstructParticle() override {
        PYBIND11_OVERLOAD_PURE(void,
                               G4VUserPhysicsList,
                               ConstructParticle,
        );
    }

    // Trampoline (need one for each virtual function)
    void ConstructProcess() override {
        PYBIND11_OVERLOAD_PURE(void,
                               G4VUserPhysicsList,
                               ConstructProcess,
        );
    }

    // Trampoline (need one for each virtual function)
    void SetCuts() override {
        PYBIND11_OVERLOAD(void,
                          G4VUserPhysicsList,
                          SetCuts,
        );
    }

};

// main wrapper
void init_G4VUserPhysicsList(py::module &m) {

    py::class_<G4VUserPhysicsList, PyG4VUserPhysicsList>(m, "G4VUserPhysicsList")

        .def(py::init<>())

        .def("ConstructParticle", &G4VUserPhysicsList::ConstructParticle)
        .def("ConstructProcess", &G4VUserPhysicsList::ConstructParticle)
        .def("SetCuts", &G4VUserPhysicsList::SetCuts)

        .def("SetDefaultCutValue", &G4VUserPhysicsList::SetDefaultCutValue)
        .def("GetDefaultCutValue", &G4VUserPhysicsList::GetDefaultCutValue)

        .def("IsPhysicsTableRetrieved", &G4VUserPhysicsList::IsPhysicsTableRetrieved)
        .def("IsStoredInAscii", &G4VUserPhysicsList::IsStoredInAscii)
        .def("GetPhysicsTableDirectory",
             &G4VUserPhysicsList::GetPhysicsTableDirectory,
             py::return_value_policy::copy)

        .def("SetStoredInAscii", &G4VUserPhysicsList::SetStoredInAscii)
        .def("ResetStoredInAscii", &G4VUserPhysicsList::ResetStoredInAscii)

        .def("DumpList", &G4VUserPhysicsList::DumpList)

        .def("DumpCutValuesTable", &G4VUserPhysicsList::DumpCutValuesTable)
        .def("DumpCutValuesTableIfRequested", &G4VUserPhysicsList::DumpCutValuesTableIfRequested)

        .def("SetVerboseLevel", &G4VUserPhysicsList::SetVerboseLevel)
        .def("GetVerboseLevel", &G4VUserPhysicsList::GetVerboseLevel)
        .def("SetCutsWithDefault", &G4VUserPhysicsList::SetCutsWithDefault)
        .def("SetCutsForRegion", &G4VUserPhysicsList::SetCutsForRegion)
        .def("GetApplyCuts", &G4VUserPhysicsList::GetApplyCuts);

}
