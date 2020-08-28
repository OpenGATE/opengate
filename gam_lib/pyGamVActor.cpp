/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamVActor.h"
#include "G4VPrimitiveScorer.hh"

void init_GamVActor(py::module &m) {

    py::class_<GamVActor, G4VPrimitiveScorer>(m, "GamVActor")
        .def(py::init<std::string>())
        .def("RegisterSD", &GamVActor::RegisterSD)
        .def("BeforeStart", &GamVActor::BeforeStart)
        .def_readwrite("actions", &GamVActor::actions)
        .def_readonly("batch_step_count", &GamVActor::batch_step_count)
        .def_readwrite("batch_size", &GamVActor::batch_size)
        .def("ProcessBatch", &GamVActor::ProcessBatch)
        .def("EndOfRunAction", &GamVActor::EndOfRunAction);
}

