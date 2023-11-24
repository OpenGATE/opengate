/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/functional.h>
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GatePhaseSpaceSource.h"

void init_GatePhaseSpaceSource(py::module &m) {

  py::class_<GatePhaseSpaceSource, GateVSource>(m, "GatePhaseSpaceSource")
      .def(py::init())
      .def("InitializeUserInfo", &GatePhaseSpaceSource::InitializeUserInfo)
      .def("SetGeneratorFunction", &GatePhaseSpaceSource::SetGeneratorFunction)

      .def("SetEnergyBatch", &GatePhaseSpaceSource::SetEnergyBatch)
      .def("SetWeightBatch", &GatePhaseSpaceSource::SetWeightBatch)
      .def("SetPDGCodeBatch", &GatePhaseSpaceSource::SetPDGCodeBatch)

      .def("SetPositionXBatch", &GatePhaseSpaceSource::SetPositionXBatch)
      .def("SetPositionYBatch", &GatePhaseSpaceSource::SetPositionYBatch)
      .def("SetPositionZBatch", &GatePhaseSpaceSource::SetPositionZBatch)

      .def("SetDirectionXBatch", &GatePhaseSpaceSource::SetDirectionXBatch)
      .def("SetDirectionYBatch", &GatePhaseSpaceSource::SetDirectionYBatch)
      .def("SetDirectionZBatch", &GatePhaseSpaceSource::SetDirectionZBatch);
}
