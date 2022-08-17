/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateDoseActor.h"

void init_GateDoseActor(py::module &m) {
    py::class_<GateDoseActor,
        std::unique_ptr<GateDoseActor, py::nodelete>, GateVActor>(m, "GateDoseActor")
        .def(py::init<py::dict &>())
        .def_readwrite("cpp_edep_image", &GateDoseActor::cpp_edep_image)
        .def_readwrite("cpp_square_image", &GateDoseActor::cpp_square_image)
        .def_readwrite("cpp_temp_image", &GateDoseActor::cpp_temp_image)
        .def_readwrite("cpp_dose_image", &GateDoseActor::cpp_dose_image)
        .def_readwrite("cpp_last_id_image", &GateDoseActor::cpp_last_id_image)
        .def_readwrite("fPhysicalVolumeName", &GateDoseActor::fPhysicalVolumeName);
}

