/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

#include "G4VUserDetectorConstruction.hh"
#include "G4VPhysicalVolume.hh"

namespace py = pybind11;

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html
// Needed helper class because of the pure virtual method
class PyG4VUserDetectorConstruction : public G4VUserDetectorConstruction {
public:
    // Inherit the constructors
    using G4VUserDetectorConstruction::G4VUserDetectorConstruction;

    // Trampoline (need one for each virtual function)
    G4VPhysicalVolume *Construct() override {
        // std::cout << "I am in PyG4VUserDetectorConstruction::Construct" << std::endl;
        PYBIND11_OVERLOAD_PURE(G4VPhysicalVolume*,
                               G4VUserDetectorConstruction,
                               Construct,
        );
    }

    // Trampoline (need one for each virtual function)
    void ConstructSDandField() override {
        PYBIND11_OVERLOAD(void,
                          G4VUserDetectorConstruction,
                          ConstructSDandField,
        );
    }

};

// main python wrapper
void init_G4VUserDetectorConstruction(py::module &m) {

    /* py::nodelete is needed to prevent Python to delete this object,
     * because it is already deleted by G4RunManager */

    py::class_<G4VUserDetectorConstruction,
        std::unique_ptr<G4VUserDetectorConstruction, py::nodelete>,
        PyG4VUserDetectorConstruction>(m, "G4VUserDetectorConstruction")

        .def(py::init_alias())
        .def("Construct", &G4VUserDetectorConstruction::Construct,
             py::return_value_policy::reference_internal)
        .def("ConstructSDandField", &G4VUserDetectorConstruction::ConstructSDandField,
             py::return_value_policy::reference_internal)
        /*.def("__del__",
             [](const G4VUserDetectorConstruction &s) -> void {
                 std::cerr << "---------------> deleting G4VUserDetectorConstruction " << std::endl;
             })
             */
        ;

}
