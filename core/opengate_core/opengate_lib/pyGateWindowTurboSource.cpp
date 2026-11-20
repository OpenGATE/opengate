/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateWindowTurboSource.h"

void init_GateWindowTurboSource(py::module &m) {

  py::class_<GateWindowTurboSharedCache,
             std::shared_ptr<GateWindowTurboSharedCache>>(
      m, "GateWindowTurboSharedCache")
      .def(py::init<>())
      .def_readonly("act_ratio", &GateWindowTurboSharedCache::fActRatio)
      .def_readonly("max_solid_angle",
                    &GateWindowTurboSharedCache::fMaxSolidAngle)
      .def_readonly("init_duration",
                    &GateWindowTurboSharedCache::fInitDuration);

  py::class_<GateWindowTurboSource, GateGenericSource>(m,
                                                       "GateWindowTurboSource")
      .def(py::init())
      .def("SetSharedCache", &GateWindowTurboSource::SetSharedCache)
      .def("InitializeUserInfo", &GateWindowTurboSource::InitializeUserInfo);
}
