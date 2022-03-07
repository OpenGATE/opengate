/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "GamHelpersImage.h"

void init_GamHelpers(py::module &m) {

    py::class_<GamVolumeVoxelizer>(m, "GamVolumeVoxelizer")
        .def(py::init<>())
        .def_readwrite("fImage", &GamVolumeVoxelizer::fImage)
        .def_readonly("fLabels", &GamVolumeVoxelizer::fLabels)
        .def("Voxelize", &GamVolumeVoxelizer::Voxelize);

}

