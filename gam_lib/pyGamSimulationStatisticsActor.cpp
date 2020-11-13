/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamSimulationStatisticsActor.h"

void init_GamSimulationStatisticsActor(py::module &m) {

    py::class_<GamSimulationStatisticsActor, GamVActor>(m, "GamSimulationStatisticsActor")
        .def(py::init<std::string>())
            /*
            .def("StartSimulationAction", &GamSimulationStatisticsActor::StartSimulationAction)
            .def("EndSimulationAction", &GamSimulationStatisticsActor::EndSimulationAction)
            .def("BeginOfRunAction", &GamSimulationStatisticsActor::BeginOfRunAction)
            .def("BeginOfEventAction", &GamSimulationStatisticsActor::BeginOfEventAction)
            .def("PreUserTrackingAction", &GamSimulationStatisticsActor::PreUserTrackingAction)
            .def("SteppingBatchAction", &GamSimulationStatisticsActor::SteppingBatchAction)
             */

        .def_readwrite("run_count", &GamSimulationStatisticsActor::run_count)
        .def_readwrite("event_count", &GamSimulationStatisticsActor::event_count)
        .def_readwrite("track_count", &GamSimulationStatisticsActor::track_count)
        .def_readwrite("step_count", &GamSimulationStatisticsActor::step_count)
        .def_readwrite("duration", &GamSimulationStatisticsActor::duration);
}

