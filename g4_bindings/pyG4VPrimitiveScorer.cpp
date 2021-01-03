/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4VPrimitiveScorer.hh"
#include "G4Step.hh"

class PyG4VPrimitiveScorer : public G4VPrimitiveScorer {
public:
    /* Inherit the constructors */
    using G4VPrimitiveScorer::G4VPrimitiveScorer;


    G4bool ProcessHits(G4Step *aStep, G4TouchableHistory *aTouchable) override {
        // std::cout << "PyG4VPrimitiveScorer trampoline " << std::endl;
        PYBIND11_OVERLOAD_PURE(G4bool,
                               G4VPrimitiveScorer,
                               ProcessHits,
                               aStep, aTouchable
        );
    }

};


void init_G4VPrimitiveScorer(py::module &m) {

    py::class_<G4VPrimitiveScorer, PyG4VPrimitiveScorer>(m, "G4VPrimitiveScorer")
            .def(py::init<G4String, G4int>())
        //.def("ProcessHits", &G4VPrimitiveScorer::ProcessHits)
        //.def("UserSteppingBatchAction", &G4VPrimitiveScorer::UserSteppingBatchAction)
            ;
}

