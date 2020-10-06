/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamVActor.h"
#include "G4VPrimitiveScorer.hh"

class PyGamVActor : public GamVActor {
public:
    /* Inherit the constructors */
    using GamVActor::GamVActor;

    // Main function to be (optionally) overridden on the py side
    // Will be called every time a batch of step should be processed
    void ProcessHitsPerBatch(bool force = false) override {
        // std::cout << "PyGamVActor trampoline " << std::endl;
        PYBIND11_OVERLOAD(void,
                          GamVActor,
                          ProcessHitsPerBatch,
                          force
        );
    }

    void SteppingBatchAction() override {
        // std::cout << "PyGamSimulationStatisticsActor trampoline " << std::endl;
        PYBIND11_OVERLOAD(void,
                          GamVActor,
                          SteppingBatchAction,
        );
    }

};

void init_GamVActor(py::module &m) {

    py::class_<GamVActor, PyGamVActor>(m, "GamVActor")
        .def(py::init<std::string>())
        .def("RegisterSD", &GamVActor::RegisterSD)
        .def("BeforeStart", &GamVActor::BeforeStart)
        .def_readwrite("actions", &GamVActor::actions)
        .def_readonly("batch_step_count", &GamVActor::batch_step_count)
        .def_readwrite("batch_size", &GamVActor::batch_size)
        .def("ProcessHitsPerBatch", &GamVActor::ProcessHitsPerBatch)
        .def("SteppingBatchAction", &GamVActor::SteppingBatchAction)
        .def("EndOfRunAction", &GamVActor::EndOfRunAction);
}

