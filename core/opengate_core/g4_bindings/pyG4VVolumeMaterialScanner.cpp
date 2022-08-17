/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>
#include "G4VVolumeMaterialScanner.hh"

namespace py = pybind11;

void init_G4VVolumeMaterialScanner(py::module &m) {

    py::class_<G4VVolumeMaterialScanner>(m, "G4VVolumeMaterialScanner");
}
