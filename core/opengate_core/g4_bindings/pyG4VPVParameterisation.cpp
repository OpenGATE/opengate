/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

#include "G4VPVParameterisation.hh"

namespace py = pybind11;

void init_G4VPVParameterisation(py::module &m) {

    py::class_<G4VPVParameterisation>(m, "G4VPVParameterisation");
}
