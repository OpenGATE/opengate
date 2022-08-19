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

#include "GateGANSource.h"

void init_GateGANSource(py::module &m) {

    py::class_<GateGANSource, GateGenericSource>(m, "GateGANSource")
        .def(py::init())
        .def("SetGeneratorFunction", &GateGANSource::SetGeneratorFunction)
        .def("InitializeUserInfo", &GateGANSource::InitializeUserInfo)

        .def_readwrite("fPositionX", &GateGANSource::fPositionX)
        .def_readwrite("fPositionY", &GateGANSource::fPositionY)
        .def_readwrite("fPositionZ", &GateGANSource::fPositionZ)
        .def_readwrite("fDirectionX", &GateGANSource::fDirectionX)
        .def_readwrite("fDirectionY", &GateGANSource::fDirectionY)
        .def_readwrite("fDirectionZ", &GateGANSource::fDirectionZ)
        .def_readwrite("fEnergy", &GateGANSource::fEnergy)
        .def_readwrite("fWeight", &GateGANSource::fWeight)
        .def_readwrite("fTime", &GateGANSource::fTime)

        .def_readwrite("fPositionX2", &GateGANSource::fPositionX2)
        .def_readwrite("fPositionY2", &GateGANSource::fPositionY2)
        .def_readwrite("fPositionZ2", &GateGANSource::fPositionZ2)
        .def_readwrite("fDirectionX2", &GateGANSource::fDirectionX2)
        .def_readwrite("fDirectionY2", &GateGANSource::fDirectionY2)
        .def_readwrite("fDirectionZ2", &GateGANSource::fDirectionZ2)
        .def_readwrite("fEnergy2", &GateGANSource::fEnergy2)
        .def_readwrite("fWeight2", &GateGANSource::fWeight2)
        .def_readwrite("fTime2", &GateGANSource::fTime2)

        .def_readwrite("fUseWeight", &GateGANSource::fUseWeight)
        .def_readwrite("fUseTime", &GateGANSource::fUseTime)
        .def_readwrite("fUseTimeRelative", &GateGANSource::fUseTimeRelative)
        .def_readonly("fNumberOfSkippedParticles", &GateGANSource::fNumberOfSkippedParticles);
}

