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

#include "GamARFActor.h"

void init_GamARFActor(py::module &m) {
    py::class_<GamARFActor,
        std::unique_ptr<GamARFActor, py::nodelete>, GamVActor>(m, "GamARFActor")
        .def(py::init<py::dict &>())
        .def("SetARFFunction", &GamARFActor::SetARFFunction) // FIXME, unsure what to do, seg fault after dest
        .def_readonly("fCurrentNumberOfHits", &GamARFActor::fCurrentNumberOfHits)
        .def_readonly("fEnergy", &GamARFActor::fEnergy)
        .def_readonly("fPositionX", &GamARFActor::fPositionX)
        .def_readonly("fPositionY", &GamARFActor::fPositionY)
        .def_readonly("fDirectionX", &GamARFActor::fDirectionX)
        .def_readonly("fDirectionY", &GamARFActor::fDirectionY);
}

