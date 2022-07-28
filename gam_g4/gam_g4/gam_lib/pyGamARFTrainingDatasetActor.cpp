/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

namespace py = pybind11;

#include "GamARFTrainingDatasetActor.h"
#include "GamHitsCollectionActor.h"

void init_GamARFTrainingDatasetActor(py::module &m) {
    py::class_<GamARFTrainingDatasetActor,
        std::unique_ptr<GamARFTrainingDatasetActor, py::nodelete>,
        GamHitsCollectionActor>(m, "GamARFTrainingDatasetActor")
        .def(py::init<py::dict &>());
}

