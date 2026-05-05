/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4EquationOfMotion.hh"
#include "G4Mag_EqRhs.hh"

void init_G4Mag_EqRhs(py::module &m) {

  py::class_<G4Mag_EqRhs, G4EquationOfMotion,
             std::unique_ptr<G4Mag_EqRhs, py::nodelete>>(m, "G4Mag_EqRhs")

      ;
}
