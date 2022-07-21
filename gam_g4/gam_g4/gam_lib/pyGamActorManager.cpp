/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamActorManager.h"

void init_GamActorManager(py::module &m) {
    py::class_<GamActorManager,
        std::unique_ptr<GamActorManager, py::nodelete>>(m, "GamActorManager")
        .def(py::init());
}

