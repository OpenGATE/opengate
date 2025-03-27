/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4Isotope.hh"

void init_G4Isotope(py::module &m) {
  py::class_<G4Isotope>(m, "G4Isotope")

      // name Z N A
      .def(py::init<const G4String &, G4double, G4double, G4double>())

      .def("__repr__",
           [](const G4Isotope &Isotope) {
             std::ostringstream flux;
             flux << Isotope;
             return flux.str();
           })

      .def("GetName", &G4Isotope::GetName, py::return_value_policy::reference)
      .def("GetZ", &G4Isotope::GetZ)
      .def("GetN", &G4Isotope::GetN)
      .def("GetA", &G4Isotope::GetA);
}
