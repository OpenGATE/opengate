/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4UniformMagneticField.hh"

void init_G4UniformMagneticField(py::module &m) {
  py::class_<G4UniformMagneticField, std::unique_ptr<G4UniformMagneticField, py::nodelete>>(
      m, "G4UniformMagneticField")

    .def(py::init<const G4ThreeVector &>())
    // TODO: add other methods
}
