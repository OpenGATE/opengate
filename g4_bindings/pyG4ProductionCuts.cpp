/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4ProductionCuts.hh"

void init_G4ProductionCuts(py::module &m) {

    py::class_<G4ProductionCuts>(m, "G4ProductionCuts")
        .def(py::init())
        .def("SetProductionCut",
             py::overload_cast<G4double, const G4String &>(&G4ProductionCuts::SetProductionCut))
        .def("GetProductionCut",
             py::overload_cast<const G4String &>(&G4ProductionCuts::GetProductionCut, py::const_));
}

