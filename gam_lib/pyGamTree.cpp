/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GamTree.h"

void init_GamTree(py::module &m) {
    py::class_<GamTree, std::unique_ptr<GamTree, py::nodelete>>(m, "GamTree")
            .def_readwrite("fTreeName", &GamTree::fTreeName)
            .def_readonly("fHitAttributes", &GamTree::fBranches)
            .def_readonly("fHitAttributeMap", &GamTree::fBranchesMap)
            .def("FreeBranches", &GamTree::FreeBranches)
            .def("GetHitBranch", &GamTree::GetBranch)
            .def("WriteToRoot", &GamTree::WriteToRoot)
            .def("GetNTuple", &GamTree::GetNTuple);
}

