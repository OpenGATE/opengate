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

    py::class_<GamSimulationStatisticsActor,
            std::unique_ptr<GamSimulationStatisticsActor, py::nodelete>,
            GamVActor>(m, "GamSimulationStatisticsActor")
            .def(py::init<std::string>())

            .def("GetRunCount", &GamSimulationStatisticsActor::GetRunCount)
            .def("GetEventCount", &GamSimulationStatisticsActor::GetEventCount)
            .def("GetTrackCount", &GamSimulationStatisticsActor::GetTrackCount)
            .def("GetStepCount", &GamSimulationStatisticsActor::GetStepCount)

            .def("SetRunCount", &GamSimulationStatisticsActor::SetRunCount)
            .def("SetEventCount", &GamSimulationStatisticsActor::SetEventCount)
            .def("SetTrackCount", &GamSimulationStatisticsActor::SetTrackCount)
            .def("SetStepCount", &GamSimulationStatisticsActor::SetStepCount)

            .def_readwrite("fDuration", &GamSimulationStatisticsActor::fDuration);
}

