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

#include "GatePhaseSpaceSource.h"

void init_GatePhaseSpaceSource(py::module &m) {

  py::class_<GatePhaseSpaceSource, GateVSource>(m, "GatePhaseSpaceSource")
      .def(py::init())
      .def("InitializeUserInfo", &GatePhaseSpaceSource::InitializeUserInfo)
      .def("SetGeneratorFunction", &GatePhaseSpaceSource::SetGeneratorFunction)
      //.def("SetGeneratorInfo", &GatePhaseSpaceSource::SetGeneratorInfo)

      .def_readwrite("fPDGCode", &GatePhaseSpaceSource::fPDGCode)
      .def_readwrite("fParticleName", &GatePhaseSpaceSource::fParticleName)

      .def_readwrite("fPositionX", &GatePhaseSpaceSource::fPositionX)
      .def_readwrite("fPositionY", &GatePhaseSpaceSource::fPositionY)
      .def_readwrite("fPositionZ", &GatePhaseSpaceSource::fPositionZ)

      .def_readwrite("fDirectionX", &GatePhaseSpaceSource::fDirectionX)
      .def_readwrite("fDirectionY", &GatePhaseSpaceSource::fDirectionY)
      .def_readwrite("fDirectionZ", &GatePhaseSpaceSource::fDirectionZ)

      .def_readwrite("fEnergy", &GatePhaseSpaceSource::fEnergy)
      .def_readwrite("fWeight", &GatePhaseSpaceSource::fWeight)
      // .def_readwrite("fTime", &GatePhaseSpaceSource::fTime)
      ;
}
