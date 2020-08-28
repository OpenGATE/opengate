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

#include "G4Step.hh"
#include "GamDoseActor2.h"

PYBIND11_MAKE_OPAQUE(std::vector<G4ThreeVector>);

class PyGamDoseActor2 : public GamDoseActor2 {
public:
    /* Inherit the constructors */
    using GamDoseActor2::GamDoseActor2;

    void SteppingBatchAction() override {
        // std::cout << "PyGamDoseActor SteppingBatchAction trampoline " << std::endl;
        PYBIND11_OVERLOAD(void,
                          GamDoseActor2,
                          SteppingBatchAction,
        );
    }

};

void init_GamDoseActor2(py::module &m) {
    py::class_<GamDoseActor2, PyGamDoseActor2, GamVActor>(m, "GamDoseActor2")
        .def(py::init())
        .def("SteppingBatchAction", &GamDoseActor2::SteppingBatchAction)
        .def_readonly("vpositions", &GamDoseActor2::vpositions);
    py::bind_vector<std::vector<G4ThreeVector>>(m, "VectorG4ThreeVector");
}

