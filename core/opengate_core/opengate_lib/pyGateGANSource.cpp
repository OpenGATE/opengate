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

#include "GateGANSource.h"

void init_GateGANSource(py::module &m) {

  py::class_<GateGANSource, GateGenericSource>(m, "GateGANSource")
      .def(py::init())
      .def("InitializeUserInfo", &GateGANSource::InitializeUserInfo)
      .def("SetGeneratorFunction", &GateGANSource::SetGeneratorFunction)
      .def("SetGeneratorInfo", &GateGANSource::SetGeneratorInfo)

      .def_readwrite("fPositionX", &GateGANSource::fPositionX)
      .def_readwrite("fPositionY", &GateGANSource::fPositionY)
      .def_readwrite("fPositionZ", &GateGANSource::fPositionZ)

      .def_readwrite("fDirectionX", &GateGANSource::fDirectionX)
      .def_readwrite("fDirectionY", &GateGANSource::fDirectionY)
      .def_readwrite("fDirectionZ", &GateGANSource::fDirectionZ)

      .def_readwrite("fEnergy", &GateGANSource::fEnergy)
      .def_readwrite("fWeight", &GateGANSource::fWeight)
      .def_readwrite("fTime", &GateGANSource::fTime);
}
