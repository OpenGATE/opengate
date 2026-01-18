/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateCoincidenceSorterActor.h"

void init_GateCoincidenceSorterActor(py::module &m) {

  py::class_<GateCoincidenceSorterActor,
             std::unique_ptr<GateCoincidenceSorterActor, py::nodelete>,
             GateVDigitizerWithOutputActor>(m, "GateCoincidenceSorterActor")
      .def(py::init<py::dict &>())
      .def("SetGroupVolumeDepth",
           &GateCoincidenceSorterActor::SetGroupVolumeDepth);
}
