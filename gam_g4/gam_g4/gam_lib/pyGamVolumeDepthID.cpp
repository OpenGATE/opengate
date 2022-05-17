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

#include "GamUniqueVolumeID.h"

void init_GamVolumeDepthID(py::module &m) {
    py::class_<GamUniqueVolumeID::VolumeDepthID>(m, "GamVolumeDepthID")
            .def_readonly("fVolumeName", &GamUniqueVolumeID::VolumeDepthID::fVolumeName)
            .def_readonly("fCopyNb", &GamUniqueVolumeID::VolumeDepthID::fCopyNb)
            .def_readonly("fDepth", &GamUniqueVolumeID::VolumeDepthID::fDepth)
            //.def_readonly("fTransform", &GamUniqueVolumeID::VolumeDepthID::fTransform)
            .def_readonly("fTranslation", &GamUniqueVolumeID::VolumeDepthID::fTranslation)
            .def_readonly("fRotation", &GamUniqueVolumeID::VolumeDepthID::fRotation)
            .def_readonly("fVolume", &GamUniqueVolumeID::VolumeDepthID::fVolume);
}

