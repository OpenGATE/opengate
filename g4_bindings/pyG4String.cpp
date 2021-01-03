/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>
#include <pybind11/operators.h>

namespace py = pybind11;

#include "G4String.hh"

void init_G4String(py::module &m) {

    py::class_<G4String>(m, "G4String", "string class")

            // Constructor
            .def(py::init())
            .def(py::init<const G4String &>())
            .def(py::init<const char *>())

                    // Operators // FIXME
                    //.def(py::self_ns::str(py::self))
            .def(py::self + py::self)
            .def(py::self += py::self)
                    //.def(py::self += other<const char*>())
            .def(py::self == py::self)
                    //.def(py::self == other<const char*>())
            .def(py::self != py::self)
                    //.def(py::self != other<const char*>())

                    // stream output
                    // FIXME not sure this is the right way to do
            .def("__repr__", [](const G4String &a) {
                std::ostringstream os;
                os << a;
                return os.str();
            });

    // py::implicitly_convertible<G4String, const char*>();
    py::implicitly_convertible<const char *, G4String>();
    // py::implicitly_convertible<G4String, std::string>();
    // py::implicitly_convertible<std::string ,G4String>();
}
