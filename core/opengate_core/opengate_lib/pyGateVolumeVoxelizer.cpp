/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateVolumeVoxelizer.h"

void init_GateVolumeVoxelizer(py::module &m) {

  py::class_<GateVolumeVoxelizer>(m, "GateVolumeVoxelizer")
      .def(py::init<>())
      .def_readwrite("fImage", &GateVolumeVoxelizer::fImage)
      .def_readonly("fLabels", &GateVolumeVoxelizer::fLabels)
      .def("GetIndexIsoCenter",
           [](const GateVolumeVoxelizer &self) -> std::vector<float> {
             std::vector<float> c = {self.fIndexIsoCenter[0],
                                     self.fIndexIsoCenter[1],
                                     self.fIndexIsoCenter[2]};
             return c;
           })
      .def("Voxelize", &GateVolumeVoxelizer::Voxelize);
}
