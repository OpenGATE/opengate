/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Track.hh"
#include "G4UserLimits.hh"

void init_G4UserLimits(py::module &m) {
  py::class_<G4UserLimits>(m, "G4UserLimits")
      //  multiple overloaded constructors
      .def(py::init<G4double>())
      .def(py::init<G4double, G4double>())
      .def(py::init<G4double, G4double, G4double>())
      .def(py::init<G4double, G4double, G4double, G4double>())
      .def(py::init<G4double, G4double, G4double, G4double, G4double>())
      // ---
      .def(py::init<const G4String &>())
      .def(py::init<const G4String &, G4double>())
      .def(py::init<const G4String &, G4double, G4double>())
      .def(py::init<const G4String &, G4double, G4double, G4double>())
      .def(py::init<const G4String &, G4double, G4double, G4double, G4double>())
      .def(py::init<const G4String &, G4double, G4double, G4double, G4double,
                    G4double>())

      // Only method needed for now. Might have to be expanded
      .def("SetMaxAllowedStep", &G4UserLimits::SetMaxAllowedStep);
}
