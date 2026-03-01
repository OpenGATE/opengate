/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>
namespace py = pybind11;

#include "GateVBiasOptrActor.h"
#include "GateChannelXSScalingOptrActor.h"

void init_GateChannelXSScalingOptrActor(py::module &m) {
  py::class_<GateChannelXSScalingOptrActor, GateVBiasOptrActor>(
      m, "GateChannelXSScalingOptrActor")
      .def(py::init<py::dict &>())
      .def("ConfigureForWorker", &GateChannelXSScalingOptrActor::ConfigureForWorker)
      .def("ClearOperators",     &GateChannelXSScalingOptrActor::ClearOperators);
}
