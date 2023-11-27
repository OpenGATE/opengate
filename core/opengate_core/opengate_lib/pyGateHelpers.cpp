/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GateHelpersDict.h"
#include "GateVolumeVoxelizer.h"

void init_GateHelpers(py::module &m) {

  py::class_<GateVolumeVoxelizer>(m, "GateVolumeVoxelizer")
      .def(py::init<>())
      .def_readwrite("fImage", &GateVolumeVoxelizer::fImage)
      .def_readonly("fLabels", &GateVolumeVoxelizer::fLabels)
      .def("Voxelize", &GateVolumeVoxelizer::Voxelize);

  m.def("DictGetG4RotationMatrix", DictGetG4RotationMatrix);
}
