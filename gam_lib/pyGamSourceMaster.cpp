/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamSourceMaster.h"
#include "G4Event.hh"

// https://pybind11.readthedocs.io/en/stable/advanced/classes.html
// Needed helper class because of the pure virtual method
class PyGamSourceMaster : public GamSourceMaster {
public:
    // Inherit the constructors
    using GamSourceMaster::GamSourceMaster;

    // Trampoline (need one for each virtual function)
    void GeneratePrimaries(G4Event *anEvent) override {
        PYBIND11_OVERLOAD(void,
                          GamSourceMaster,
                          GeneratePrimaries,
                          anEvent
        );
    }

};

// Main wrapper
void init_GamSourceMaster(py::module &m) {

    py::class_<GamSourceMaster, PyGamSourceMaster>(m, "GamSourceMaster")
        //py::class_<GamSourceMaster, G4VUserPrimaryGeneratorAction>(m, "GamSourceMaster")
        .def(py::init())
        .def("GeneratePrimaries", &GamSourceMaster::GeneratePrimaries);
}
