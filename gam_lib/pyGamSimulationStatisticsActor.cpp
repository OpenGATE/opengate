/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/stl_bind.h>

#include "G4Step.hh"

namespace py = pybind11;

#include "GamSimulationStatisticsActor.h"

class PyGamSimulationStatisticsActor : public GamSimulationStatisticsActor {
public:
    /* Inherit the constructors */
    using GamSimulationStatisticsActor::GamSimulationStatisticsActor;

    /*
    void BeginOfEventAction(const G4Event *event) {
        //std::cout << "PyGamSimulationStatisticsActor event trampoline " << std::endl;
        PYBIND11_OVERLOAD(void,
                          GamSimulationStatisticsActor,
                          BeginOfEventAction,
                          event
        );
    }

    void SteppingAction(G4Step *step) {
        //std::cout << "PyGamSimulationStatisticsActor step trampoline " << std::endl;
        PYBIND11_OVERLOAD(void,
                          GamSimulationStatisticsActor,
                          SteppingAction,
                          step
        );
    }
*/

    void SteppingBatchAction() override {
        // std::cout << "PyGamSimulationStatisticsActor trampoline " << std::endl;
        PYBIND11_OVERLOAD(void,
                          GamSimulationStatisticsActor,
                          SteppingBatchAction,
        );
    }

};

void init_GamSimulationStatisticsActor(py::module &m) {
    py::class_<GamSimulationStatisticsActor, PyGamSimulationStatisticsActor, GamVActor>(m,
                                                                                        "GamSimulationStatisticsActor")
        .def(py::init())
        .def("SteppingBatchAction", &GamSimulationStatisticsActor::SteppingBatchAction)
        .def_readonly("step_count", &GamSimulationStatisticsActor::step_count);
}

