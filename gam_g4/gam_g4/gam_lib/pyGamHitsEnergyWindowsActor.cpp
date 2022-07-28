/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamHitsEnergyWindowsActor.h"

void init_GamHitsEnergyWindowsActor(py::module &m) {

    py::class_<GamHitsEnergyWindowsActor,
        std::unique_ptr<GamHitsEnergyWindowsActor, py::nodelete>,
        GamVActor>(m, "GamHitsEnergyWindowsActor")
        .def(py::init<py::dict &>());
}

