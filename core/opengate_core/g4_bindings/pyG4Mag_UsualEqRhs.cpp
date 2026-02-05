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
#include "G4Mag_UsualEqRhs.hh"
#include "G4MagneticField.hh"

void init_G4Mag_UsualEqRhs(py::module &m) {

  py::class_<G4Mag_UsualEqRhs, G4Mag_EqRhs, std::unique_ptr<G4Mag_UsualEqRhs, py::nodelete>>(
      m, "G4Mag_UsualEqRhs")

    .def(py::init<G4MagneticField *>())

    .def("EvaluateRhsGivenB", &G4Mag_UsualEqRhs::EvaluateRhsGivenB)
    .def("SetChargeMomentumMass", &G4Mag_UsualEqRhs::SetChargeMomentumMass)

    ;

}
