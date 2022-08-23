/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateARFTrainingDatasetActor.h"
#include "GateHitsCollectionActor.h"

void init_GateARFTrainingDatasetActor(py::module &m) {
  py::class_<GateARFTrainingDatasetActor,
             std::unique_ptr<GateARFTrainingDatasetActor, py::nodelete>,
             GateHitsCollectionActor>(m, "GateARFTrainingDatasetActor")
      .def(py::init<py::dict &>());
}
