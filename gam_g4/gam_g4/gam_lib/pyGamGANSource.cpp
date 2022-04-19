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

#include "GamGANSource.h"

void init_GamGANSource(py::module &m) {

    py::class_<GamGANSource, GamGenericSource>(m, "GamGANSource")
        //.def(py::init<GamGANSource::ParticleGeneratorType>())
        .def(py::init())
        .def("SetGeneratorFunction", &GamGANSource::SetGeneratorFunction)
        .def("InitializeUserInfo", &GamGANSource::InitializeUserInfo)
        .def_readwrite("fPositionX", &GamGANSource::fPositionX)
        .def_readwrite("fPositionY", &GamGANSource::fPositionY)
        .def_readwrite("fPositionZ", &GamGANSource::fPositionZ)
        .def_readwrite("fDirectionX", &GamGANSource::fDirectionX)
        .def_readwrite("fDirectionY", &GamGANSource::fDirectionY)
        .def_readwrite("fDirectionZ", &GamGANSource::fDirectionZ)
        .def_readwrite("fEnergy", &GamGANSource::fEnergy)
        .def_readwrite("fWeight", &GamGANSource::fWeight)
        .def_readonly("fNumberOfNegativeEnergy", &GamGANSource::fNumberOfNegativeEnergy);
}

