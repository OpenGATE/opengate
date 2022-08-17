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

#include "GateUniqueVolumeID.h"

void init_GateVolumeDepthID(py::module &m) {
    py::class_<GateUniqueVolumeID::VolumeDepthID>(m, "GateVolumeDepthID")
        .def_readonly("fVolumeName", &GateUniqueVolumeID::VolumeDepthID::fVolumeName)
        .def_readonly("fCopyNb", &GateUniqueVolumeID::VolumeDepthID::fCopyNb)
        .def_readonly("fDepth", &GateUniqueVolumeID::VolumeDepthID::fDepth)
        .def_readonly("fTranslation", &GateUniqueVolumeID::VolumeDepthID::fTranslation)
        .def_readonly("fRotation", &GateUniqueVolumeID::VolumeDepthID::fRotation)
        .def_readonly("fVolume", &GateUniqueVolumeID::VolumeDepthID::fVolume);
}

