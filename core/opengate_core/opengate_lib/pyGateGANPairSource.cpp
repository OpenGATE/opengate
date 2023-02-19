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

#include "GateGANPairSource.h"

void init_GateGANPairSource(py::module &m) {

  py::class_<GateGANPairSource, GateGANSource>(m, "GateGANPairSource")
      .def(py::init())
      /*.def("SetGeneratorFunction", &GateGANPairSource::SetGeneratorFunction)
      .def("InitializeUserInfo", &GateGANPairSource::InitializeUserInfo)
      */

      // FIXME to clean

      .def_readwrite("fPositionX", &GateGANPairSource::fPositionX)
      .def_readwrite("fPositionY", &GateGANPairSource::fPositionY)
      .def_readwrite("fPositionZ", &GateGANPairSource::fPositionZ)
      .def_readwrite("fDirectionX", &GateGANPairSource::fDirectionX)
      .def_readwrite("fDirectionY", &GateGANPairSource::fDirectionY)
      .def_readwrite("fDirectionZ", &GateGANPairSource::fDirectionZ)
      .def_readwrite("fEnergy", &GateGANPairSource::fEnergy)
      .def_readwrite("fWeight", &GateGANPairSource::fWeight)
      .def_readwrite("fTime", &GateGANPairSource::fTime)

      .def_readwrite("fPositionX2", &GateGANPairSource::fPositionX2)
      .def_readwrite("fPositionY2", &GateGANPairSource::fPositionY2)
      .def_readwrite("fPositionZ2", &GateGANPairSource::fPositionZ2)
      .def_readwrite("fDirectionX2", &GateGANPairSource::fDirectionX2)
      .def_readwrite("fDirectionY2", &GateGANPairSource::fDirectionY2)
      .def_readwrite("fDirectionZ2", &GateGANPairSource::fDirectionZ2)
      .def_readwrite("fEnergy2", &GateGANPairSource::fEnergy2)
      .def_readwrite("fWeight2", &GateGANPairSource::fWeight2)
      .def_readwrite("fTime2", &GateGANPairSource::fTime2);

  /*.def_readwrite("fUseWeight", &GateGANPairSource::fUseWeight)
  .def_readwrite("fUseTime", &GateGANPairSource::fUseTime)
  .def_readwrite("fRelativeTiming", &GateGANPairSource::fRelativeTiming);*/
}
