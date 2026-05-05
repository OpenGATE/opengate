/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4ChordFinder.hh"
#include "G4MagIntegratorStepper.hh"
#include "G4MagneticField.hh"
#include "G4VIntegrationDriver.hh"

void init_G4ChordFinder(py::module &m) {
  py::class_<G4ChordFinder, std::unique_ptr<G4ChordFinder, py::nodelete>>(
      m, "G4ChordFinder")

      .def(py::init<G4VIntegrationDriver *>())
      .def(py::init<G4MagneticField *, G4double, G4MagIntegratorStepper *,
                    G4int>())

      .def("SetDeltaChord", &G4ChordFinder::SetDeltaChord);
}
