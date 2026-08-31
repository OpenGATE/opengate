/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateCoincidenceSorterActor.h"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

void init_GateCoincidenceSorterActor(py::module &m) {

  py::class_<GateCoincidenceSorterActor,
             std::unique_ptr<GateCoincidenceSorterActor, py::nodelete>,
             GateVDigitizerWithOutputActor>(m, "GateCoincidenceSorterActor")
      .def(py::init<py::dict &>())
      .def("SetGroupVolumeDepth",
           &GateCoincidenceSorterActor::SetGroupVolumeDepth);
}
