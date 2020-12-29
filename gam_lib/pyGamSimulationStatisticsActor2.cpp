/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamSimulationStatisticsActor2.h"

void init_GamSimulationStatisticsActor2(py::module &m) {

    py::class_<GamSimulationStatisticsActor2, GamVActor>(m, "GamSimulationStatisticsActor2")
        .def(py::init<std::string>())
            /*
            .def("StartSimulationAction", &GamSimulationStatisticsActor2::StartSimulationAction)
            .def("EndSimulationAction", &GamSimulationStatisticsActor2::EndSimulationAction)
            .def("BeginOfRunAction", &GamSimulationStatisticsActor2::BeginOfRunAction)
            .def("BeginOfEventAction", &GamSimulationStatisticsActor2::BeginOfEventAction)
            .def("PreUserTrackingAction", &GamSimulationStatisticsActor2::PreUserTrackingAction)
            .def("SteppingBatchAction", &GamSimulationStatisticsActor2::SteppingBatchAction)
             */

        .def_readwrite("run_count", &GamSimulationStatisticsActor2::run_count)
        .def_readwrite("event_count", &GamSimulationStatisticsActor2::event_count)
        .def_readwrite("track_count", &GamSimulationStatisticsActor2::track_count)
        .def_readwrite("step_count", &GamSimulationStatisticsActor2::step_count)
        .def_readwrite("duration", &GamSimulationStatisticsActor2::duration);
}

