/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4UserSpecialCuts.hh"
#include "G4VProcess.hh"

void init_G4UserSpecialCuts(py::module &m) {

  py::class_<G4UserSpecialCuts, G4VProcess,
             std::unique_ptr<G4UserSpecialCuts, py::nodelete>>(
      m, "G4UserSpecialCuts")
      .def(py::init<const G4String &>());
}
