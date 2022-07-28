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
        .def_readwrite("fTime", &GamGANSource::fTime)

        .def_readwrite("fPositionX2", &GamGANSource::fPositionX2)
        .def_readwrite("fPositionY2", &GamGANSource::fPositionY2)
        .def_readwrite("fPositionZ2", &GamGANSource::fPositionZ2)
        .def_readwrite("fDirectionX2", &GamGANSource::fDirectionX2)
        .def_readwrite("fDirectionY2", &GamGANSource::fDirectionY2)
        .def_readwrite("fDirectionZ2", &GamGANSource::fDirectionZ2)
        .def_readwrite("fEnergy2", &GamGANSource::fEnergy2)
        .def_readwrite("fWeight2", &GamGANSource::fWeight2)
        .def_readwrite("fTime2", &GamGANSource::fTime2)

        .def_readwrite("fUseWeight", &GamGANSource::fUseWeight)
        .def_readwrite("fUseTime", &GamGANSource::fUseTime)
        .def_readwrite("fUseTimeRelative", &GamGANSource::fUseTimeRelative)
        .def_readonly("fNumberOfSkippedParticles", &GamGANSource::fNumberOfSkippedParticles);
}

