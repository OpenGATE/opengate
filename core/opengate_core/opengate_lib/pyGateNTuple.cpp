/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4RootAnalysisManager.hh"

void init_GateNTuple(py::module &m) {
    py::class_<tools::wroot::ntuple>(m, "GateNTuple")
        .def("entries", &tools::wroot::ntuple::entries);
}

