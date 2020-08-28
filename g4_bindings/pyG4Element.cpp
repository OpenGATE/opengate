/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4Element.hh"

void init_G4Element(py::module &m) {

    py::class_<G4Element>(m, "G4Element")

        // name symbol Zeff Aeff
        .def(py::init<const G4String &, const G4String &, G4double, G4double>())

        // name symbol nbIsotopes
        //.def(py::init<const G4String &, const G4String &, G4int>())

        // stream output // FIXME not sure this is the right way to do
        .def("__repr__", [](const G4Element &Element) {
            std::ostringstream flux;
            flux << Element;
            return flux.str();
        })

        .def("GetName", &G4Element::GetName, py::return_value_policy::reference)
        .def("GetSymbol", &G4Element::GetSymbol, py::return_value_policy::reference)
        .def("GetZ", &G4Element::GetZ)
        .def("GetA", &G4Element::GetA);
}

