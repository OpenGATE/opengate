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

#include "GamVBranch.h"

void init_GamBranch(py::module &m) {
    py::class_<GamVBranch, std::unique_ptr<GamVBranch, py::nodelete>>(m, "GamBranch")
        .def_readwrite("fHitAttributeName", &GamVBranch::fBranchName)
        .def_readonly("fHitAttributeType", &GamVBranch::fBranchType)
        .def_readonly("fHitAttributeId", &GamVBranch::fBranchId)
        .def("size", &GamVBranch::size)
        .def("push_back_double", &GamVBranch::push_back_double)
        .def("DefineBranch", &GamVBranch::DefineBranch)
        .def("GetValuesAsDouble", &GamVBranch::GetValuesAsDouble)
        .def("FreeAvailableBranches", &GamVBranch::FreeAvailableBranches)
        .def("GetAvailableBranches", &GamVBranch::GetAvailableBranches);
}

